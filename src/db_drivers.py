#!/usr/bin/env python3
# **************************************************************************** #
#                                                                              #
#                                                        ::::::::   ::::::::   #
#    db_drivers.py                                     :+:    :+: :+:    :+:   #
#                                                     +:+        +:+           #
#    By: Ser Superior <marcioeduine@gmail.com>       +#++:++#++ +#++:++#++     #
#                                                          +#+        +#+      #
#    Created: 2026/07/14 08:00:00 by Ser Superior  #+#    #+# #+#    #+#       #
#    Updated: 2026/07/14 08:00:00 by Ser Superior  ########   ########         #
#                                                                              #
# **************************************************************************** #
"""Licence: GNU GPLv3 - Database driver abstraction layer (Adapter Pattern)."""

from abc import ABC, abstractmethod
import sqlite3

# Optional dependency: psycopg2 for PostgreSQL network connectivity
try:
    import psycopg2
    import psycopg2.extras
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False


class BaseDatabaseDriver(ABC):
    """Abstract base class establishing the contract for all database engine adapters."""

    # Subclasses must expose these two attributes so that existing command
    # modules (schema_commands, data_commands, export_commands, sql_engine)
    # can continue to receive a standard connection/cursor pair.
    connection = None
    cursor = None

    @abstractmethod
    def connect(self, connection_string: str) -> bool:
        """Initialise physical or network connection to the target database."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Safely close all active connection descriptors."""
        pass

    @abstractmethod
    def list_entities(self) -> list:
        """Return a unified list of tables, views, or collections available."""
        pass

    @abstractmethod
    def fetch_data(self, entity_name: str) -> tuple:
        """Return a tuple of (headers, rows) to standardise print output formats."""
        pass

    @abstractmethod
    def insert_record(self, entity_name: str, values: list) -> bool:
        """Map and execute a generic insert action into the target storage layer."""
        pass

    @abstractmethod
    def entity_exists(self, entity_name: str) -> bool:
        """Verify that the given entity name resolves in the active schema."""
        pass


class SQLiteDriver(BaseDatabaseDriver):
    """Concrete adapter for local SQLite3 engines.

    Preserves all existing PRAGMA-based introspection logic and the
    'original' template-table ordering behaviour used by insert_record.
    """

    def __init__(self) -> None:
        self.connection = None
        self.cursor = None

    def connect(self, connection_string: str) -> bool:
        """Open a SQLite3 file or in-memory database."""
        try:
            self.connection = sqlite3.connect(connection_string)
            self.cursor = self.connection.cursor()
            return True
        except Exception:
            return False

    def disconnect(self) -> None:
        """Close the active SQLite connection descriptor."""
        if self.connection:
            self.connection.close()
            self.connection = None
            self.cursor = None

    def list_entities(self) -> list:
        """Query sqlite_master for all user-defined tables and views."""
        if not self.cursor:
            return []
        self.cursor.execute(
            "SELECT name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%';"
        )
        return [row[0] for row in self.cursor.fetchall()]

    def fetch_data(self, entity_name: str) -> tuple:
        """Execute SELECT * and return (headers, rows) for the given entity."""
        if not self.cursor:
            return [], []
        try:
            self.cursor.execute(f"SELECT * FROM {entity_name};")
            headers = [desc[0] for desc in self.cursor.description]
            return headers, self.cursor.fetchall()
        except Exception:
            return [], []

    def insert_record(self, entity_name: str, values: list) -> bool:
        """Delegated insert — the full macro logic lives in data_commands.py."""
        if not (self.connection and self.cursor):
            return False
        # Type mapping and PRAGMA alignment are handled by handle_insert_command
        return True

    def entity_exists(self, entity_name: str) -> bool:
        """Return True if the entity name is present in sqlite_master."""
        if not self.cursor:
            return False
        self.cursor.execute(
            "SELECT name FROM sqlite_master WHERE name=?;",
            (entity_name,)
        )
        return self.cursor.fetchone() is not None


class PostgreSQLDriver(BaseDatabaseDriver):
    """Concrete adapter for network-bound PostgreSQL instances via psycopg2.

    The psycopg2 library is imported lazily; if it is absent the driver
    reports a clear installation hint instead of crashing at start-up.
    """

    def __init__(self) -> None:
        self.connection = None
        self.cursor = None

    def connect(self, connection_string: str) -> bool:
        """Open a TCP connection to the PostgreSQL server."""
        if not HAS_PSYCOPG2:
            print(
                "Error: The 'psycopg2' package is not installed in the active environment.\n"
                "       Install it with: pip install psycopg2-binary"
            )
            return False
        try:
            self.connection = psycopg2.connect(connection_string)
            self.cursor = self.connection.cursor()
            return True
        except Exception as error:
            print(f"Error: PostgreSQL connection failed: {error}")
            return False

    def disconnect(self) -> None:
        """Close the active PostgreSQL connection descriptor."""
        if self.connection:
            try:
                self.connection.close()
            except Exception:
                pass
            self.connection = None
            self.cursor = None

    def list_entities(self) -> list:
        """Query information_schema for all public tables."""
        if not self.cursor:
            return []
        self.cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
            """
        )
        return [row[0] for row in self.cursor.fetchall()]

    def fetch_data(self, entity_name: str) -> tuple:
        """Execute SELECT * and return (headers, rows) for the given entity."""
        if not self.cursor:
            return [], []
        try:
            self.cursor.execute(f'SELECT * FROM "{entity_name}";')
            headers = [desc[0] for desc in self.cursor.description]
            return headers, self.cursor.fetchall()
        except Exception as error:
            print(f"SQL Error: {error}")
            return [], []

    def insert_record(self, entity_name: str, values: list) -> bool:
        """Placeholder — PostgreSQL insert routing is handled by the CLI layer."""
        if not (self.connection and self.cursor):
            return False
        return True

    def entity_exists(self, entity_name: str) -> bool:
        """Return True if the entity name exists in the public schema."""
        if not self.cursor:
            return False
        try:
            self.cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = %s;
                """,
                (entity_name,)
            )
            return self.cursor.fetchone() is not None
        except Exception:
            return False

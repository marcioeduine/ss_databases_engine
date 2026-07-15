#!/usr/bin/env python3
# **************************************************************************** #
#                                                                              #
#                                                         ::::::::   ::::::::  #
#    db_drivers.py                                      :+:    :+: :+:    :+:  #
#                                                     +:+        +:+           #
#    By: Ser Superior <marcioeduine@gmail.com>        +#++:++#++ +#++:++#++    #
#                                                         +#+        +#+       #
#    Created: 2026/07/14 08:00:00 by Ser Superior  #+#    #+# #+#    #+#       #
#    Updated: 2026/07/15 21:40:00 by Ser Superior  ########   ########         #
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
    def fetch_columns_info(self, entity_name: str) -> tuple:
        """Return schema metadata for a specific entity."""
        pass

    @abstractmethod
    def fetch_data(self, entity_name: str, target_columns: list = None) -> tuple:
        """Return (headers, rows). Supports optional column projection."""
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
    """Concrete adapter for local SQLite3 engines."""

    def __init__(self) -> None:
        self.connection = None
        self.cursor = None

    def connect(self, connection_string: str) -> bool:
        try:
            self.connection = sqlite3.connect(connection_string)
            self.cursor = self.connection.cursor()
            return True
        except Exception:
            return False

    def disconnect(self) -> None:
        if self.connection:
            self.connection.close()
            self.connection = None
            self.cursor = None

    def list_entities(self) -> list:
        if not self.cursor:
            return []
        self.cursor.execute("SELECT name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%';")
        return [row[0] for row in self.cursor.fetchall()]

    def fetch_columns_info(self, entity_name: str) -> tuple:
        if not self.cursor:
            return [], []
        self.cursor.execute(f"PRAGMA table_info({entity_name});")
        headers = ["cid", "name", "type", "notnull", "dflt_value", "pk"]
        return headers, self.cursor.fetchall()

    def fetch_data(self, entity_name: str, target_columns: list = None) -> tuple:
        if not self.cursor:
            return [], []
        cols = ", ".join(target_columns) if target_columns else "*"
        self.cursor.execute(f"SELECT {cols} FROM {entity_name};")
        headers = [desc[0] for desc in self.cursor.description]
        return headers, self.cursor.fetchall()

    def insert_record(self, entity_name: str, values: list) -> bool:
        return True

    def entity_exists(self, entity_name: str) -> bool:
        if not self.cursor:
            return False
        self.cursor.execute("SELECT name FROM sqlite_master WHERE name=?;", (entity_name,))
        return self.cursor.fetchone() is not None


class PostgreSQLDriver(BaseDatabaseDriver):
    """Concrete adapter for network-bound PostgreSQL instances."""

    def __init__(self) -> None:
        self.connection = None
        self.cursor = None

    def connect(self, connection_string: str) -> bool:
        if not HAS_PSYCOPG2:
            return False
        try:
            self.connection = psycopg2.connect(connection_string)
            self.cursor = self.connection.cursor()
            return True
        except Exception:
            return False

    def disconnect(self) -> None:
        if self.connection:
            self.connection.close()
            self.connection = None
            self.cursor = None

    def list_entities(self) -> list:
        if not self.cursor:
            return []
        self.cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' ORDER BY table_name;
        """)
        return [row[0] for row in self.cursor.fetchall()]

    def fetch_columns_info(self, entity_name: str) -> tuple:
        if not self.cursor:
            return [], []
        query = """
            SELECT column_name, data_type, is_nullable, column_default 
            FROM information_schema.columns 
            WHERE table_name = %s ORDER BY ordinal_position;
        """
        self.cursor.execute(query, (entity_name,))
        headers = ["column_name", "data_type", "is_nullable", "dflt_value"]
        return headers, self.cursor.fetchall()

    def fetch_data(self, entity_name: str, target_columns: list = None) -> tuple:
        if not self.cursor:
            return [], []
        cols = ", ".join(target_columns) if target_columns else "*"
        self.cursor.execute(f'SELECT {cols} FROM "{entity_name}";')
        headers = [desc[0] for desc in self.cursor.description]
        return headers, self.cursor.fetchall()

    def insert_record(self, entity_name: str, values: list) -> bool:
        return True

    def entity_exists(self, entity_name: str) -> bool:
        if not self.cursor:
            return False
        self.cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = %s;
        """, (entity_name,))
        return self.cursor.fetchone() is not None

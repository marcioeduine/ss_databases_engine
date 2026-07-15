#!/usr/bin/env python3
# **************************************************************************** #
#                                                                              #
#                                                         ::::::::   ::::::::  #
#    db_drivers.py                                      :+:    :+: :+:    :+:  #
#                                                     +:+        +:+           #
#    By: Ser Superior <marcioeduine@gmail.com>        +#++:++#++ +#++:++#++    #
#                                                         +#+        +#+       #
#    Created: 2026/07/14 08:00:00 by Ser Superior   #+#    #+# #+#    #+#        #
#    Updated: 2026/07/15 22:40:00 by Ser Superior  ########   ########          #
#                                                                              #
# **************************************************************************** #
"""Licence: GNU GPLv3 - Database driver abstraction layer (Adapter Pattern)."""

from abc import ABC, abstractmethod
import sqlite3

try:
    import psycopg2
    import psycopg2.extensions
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False


class BaseDatabaseDriver(ABC):
    connection = None
    cursor = None

    @abstractmethod
    def connect(self, connection_string: str) -> bool: pass
    @abstractmethod
    def disconnect(self) -> None: pass
    @abstractmethod
    def list_entities(self) -> list: pass
    @abstractmethod
    def fetch_columns_info(self, entity_name: str) -> tuple: pass
    @abstractmethod
    def fetch_data(self, entity_name: str, target_columns: list = None) -> tuple: pass
    @abstractmethod
    def insert_record(self, entity_name: str, values: list) -> bool: pass
    @abstractmethod
    def entity_exists(self, entity_name: str) -> bool: pass
    @abstractmethod
    def inspect_entity(self, entity_name: str) -> dict: pass


class SQLiteDriver(BaseDatabaseDriver):
    def __init__(self) -> None:
        self.connection = None
        self.cursor = None

    def connect(self, connection_string: str) -> bool:
        try:
            self.connection = sqlite3.connect(connection_string)
            self.cursor = self.connection.cursor()
            return True
        except Exception: return False

    def disconnect(self) -> None:
        if self.connection:
            self.connection.close()
            self.connection = None
            self.cursor = None

    def list_entities(self) -> list:
        if not self.cursor: return []
        self.cursor.execute("SELECT name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%';")
        return [row[0] for row in self.cursor.fetchall()]

    def fetch_columns_info(self, entity_name: str) -> tuple:
        if not self.cursor: return [], []
        self.cursor.execute(f"PRAGMA table_info({entity_name});")
        return ["cid", "name", "type", "notnull", "dflt_value", "pk"], self.cursor.fetchall()

    def fetch_data(self, entity_name: str, target_columns: list = None) -> tuple:
        if not self.cursor: return [], []
        cols = ", ".join(target_columns) if target_columns else "*"
        self.cursor.execute(f"SELECT {cols} FROM {entity_name};")
        return [desc[0] for desc in self.cursor.description], self.cursor.fetchall()

    def insert_record(self, entity_name: str, values: list) -> bool: return True

    def entity_exists(self, entity_name: str) -> bool:
        if not self.cursor: return False
        self.cursor.execute("SELECT name FROM sqlite_master WHERE name=?;", (entity_name,))
        return self.cursor.fetchone() is not None

    def inspect_entity(self, entity_name: str) -> dict:
        if not self.cursor: return {}
        self.cursor.execute(f"PRAGMA table_info({entity_name});")
        return {"table": entity_name, "columns": self.cursor.fetchall(), "primary_key": "See 'pk' flag"}


class PostgreSQLDriver(BaseDatabaseDriver):
    def __init__(self) -> None:
        self.connection = None
        self.cursor = None

    def _rollback_if_aborted(self):
        if self.connection and self.connection.get_transaction_status() == psycopg2.extensions.TRANSACTION_STATUS_INERROR:
            self.connection.rollback()

    def connect(self, connection_string: str) -> bool:
        if not HAS_PSYCOPG2: return False
        try:
            self.connection = psycopg2.connect(connection_string)
            self.cursor = self.connection.cursor()
            return True
        except Exception: return False

    def disconnect(self) -> None:
        if self.connection:
            self.connection.close()
            self.connection = None
            self.cursor = None

    def list_entities(self) -> list:
        self._rollback_if_aborted()
        if not self.cursor: return []
        self.cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;")
        return [row[0] for row in self.cursor.fetchall()]

    def fetch_columns_info(self, entity_name: str) -> tuple:
        self._rollback_if_aborted()
        if not self.cursor: return [], []
        self.cursor.execute("SELECT column_name, data_type, is_nullable, column_default FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position;", (entity_name,))
        return ["column_name", "data_type", "is_nullable", "dflt_value"], self.cursor.fetchall()

    def fetch_data(self, entity_name: str, target_columns: list = None) -> tuple:
        self._rollback_if_aborted()
        if not self.cursor: return [], []
        cols = ", ".join(target_columns) if target_columns else "*"
        self.cursor.execute(f'SELECT {cols} FROM "{entity_name}";')
        return [desc[0] for desc in self.cursor.description], self.cursor.fetchall()

    def insert_record(self, entity_name: str, values: list) -> bool: return True

    def entity_exists(self, entity_name: str) -> bool:
        self._rollback_if_aborted()
        if not self.cursor: return False
        self.cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name = %s;", (entity_name,))
        return self.cursor.fetchone() is not None

    def inspect_entity(self, entity_name: str) -> dict:
        self._rollback_if_aborted()
        if not self.cursor: return {}
        self.cursor.execute("SELECT column_name, data_type, is_nullable, column_default FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position;", (entity_name,))
        columns = self.cursor.fetchall()
        self.cursor.execute("SELECT kcu.column_name FROM information_schema.table_constraints tc JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name WHERE tc.constraint_type = 'PRIMARY KEY' AND tc.table_name = %s;", (entity_name,))
        pk = self.cursor.fetchone()
        return {"table": entity_name, "columns": columns, "primary_key": pk[0] if pk else None}

#!/usr/bin/env python3
# **************************************************************************** #
#                                                                              #
#                                                        ::::::::   ::::::::   #
#    session_manager.py                                :+:    :+: :+:    :+:   #
#                                                     +:+        +:+           #
#    By: Ser Superior <marcioeduine@gmail.com>       +#++:++#++ +#++:++#++     #
#                                                          +#+        +#+      #
#    Created: 2026/07/14 08:00:00 by Ser Superior  #+#    #+# #+#    #+#       #
#    Updated: 2026/07/14 08:00:00 by Ser Superior  ########   ########         #
#                                                                              #
# **************************************************************************** #
"""Licence: GNU GPLv3 - Database multi-session co-ordinator."""

from typing import Dict, Optional

from db_drivers import BaseDatabaseDriver, SQLiteDriver, PostgreSQLDriver


class Session:
    """Represents an active connection context bound to a named alias."""

    def __init__(
        self,
        alias: str,
        driver: BaseDatabaseDriver,
        db_type: str,
        db_name: str
    ) -> None:
        self.alias: str = alias
        self.driver: BaseDatabaseDriver = driver
        self.db_type: str = db_type
        self.db_name: str = db_name
        self.active_table: Optional[str] = None


class SessionManager:
    """Manages multiple active database engine sessions simultaneously.

    Textual operators (not, and, or) are used throughout to align with the
    project's preferred coding aesthetic.
    """

    def __init__(self) -> None:
        self.sessions: Dict[str, Session] = {}
        self.active_alias: Optional[str] = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def register_connection(self, alias: str, conn_string: str) -> bool:
        """Parse connection string, instantiate the correct driver, and store the session."""
        if alias in self.sessions:
            print(f"Error: Connection alias '{alias}' is already registered.")
            return False

        driver, db_type, db_name = self._resolve_driver(conn_string)
        if driver is None:
            return False

        if not driver.connect(conn_string):
            print(f"Error: Connection failed to resolve target: {conn_string}")
            return False

        self.sessions[alias] = Session(alias, driver, db_type, db_name)

        # Auto-focus the first session that is registered
        if not self.active_alias:
            self.active_alias = alias

        print(f"Success: Registered connection [{alias}] linked to {db_type}://{db_name}")
        return True

    def switch_session(self, alias: str) -> bool:
        """Move the active operational focus to the target session alias."""
        if alias not in self.sessions:
            print(f"Error: Session alias '{alias}' is unknown. Run 'sessions' to list active connections.")
            return False
        self.active_alias = alias
        print(f"Switched context to session [{alias}].")
        return True

    def disconnect_session(self, alias: str) -> bool:
        """Close and remove the specified session from the active registry."""
        if alias not in self.sessions:
            print(f"Error: Session alias '{alias}' is not registered.")
            return False

        self.sessions[alias].driver.disconnect()
        del self.sessions[alias]

        # If the disconnected session was the active one, clear or reassign focus
        if self.active_alias == alias:
            remaining = list(self.sessions.keys())
            self.active_alias = remaining[0] if remaining else None
            if self.active_alias:
                print(f"Active session removed. Focus shifted to [{self.active_alias}].")
            else:
                print("Active session removed. No remaining sessions. Use 'connect' to add one.")
        else:
            print(f"Session [{alias}] disconnected successfully.")
        return True

    def get_active_session(self) -> Optional[Session]:
        """Retrieve the currently focused active session wrapper."""
        if not self.active_alias or self.active_alias not in self.sessions:
            return None
        return self.sessions[self.active_alias]

    def list_sessions(self) -> None:
        """Print a formatted table of all currently registered sessions."""
        if not self.sessions:
            print("No active sessions. Use 'connect <alias> <connection_string>' to open one.")
            return

        print("\n--- Active Sessions Registry ---")
        for alias, session in self.sessions.items():
            focus_marker = " [ACTIVE]" if alias == self.active_alias else ""
            table_info = f" | Table: {session.active_table}" if session.active_table else ""
            print(
                f"  [{alias}]{focus_marker}"
                f" | Type: {session.db_type}"
                f" | DB: {session.db_name}"
                f"{table_info}"
            )
        print("--------------------------------\n")

    # ------------------------------------------------------------------
    # Prompt string builder
    # ------------------------------------------------------------------

    def build_prompt(self, tx_active: bool = False) -> str:
        """Construct the dynamic prompt string reflecting current session context."""
        tx_tag = " [TX]" if tx_active else ""
        session = self.get_active_session()

        if not session:
            return f"SS_DB{tx_tag}> "

        table_segment = f" ({session.active_table})" if session.active_table else ""
        return f"SS_DB [{session.db_type}::{session.alias}]{table_segment}{tx_tag}> "

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_driver(self, conn_string: str) -> tuple:
        """Instantiate the correct driver based on connection string prefix.

        Returns a (driver, db_type, db_name) tuple, or (None, None, None)
        on failure.
        """
        if conn_string.startswith("postgresql://") or conn_string.startswith("postgres://"):
            db_name = conn_string.split("/")[-1] or conn_string
            return PostgreSQLDriver(), "postgres", db_name

        if conn_string.startswith("mongodb://"):
            print("Error: MongoDB adapter is not yet implemented in this release.")
            return None, None, None

        # Default: treat the connection string as a local SQLite filepath
        return SQLiteDriver(), "sqlite", conn_string

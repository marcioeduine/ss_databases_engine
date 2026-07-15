#!/usr/bin/env python3
# **************************************************************************** #
#                                                                              #
#                                                          ::::::::   :::::::: #
#    cli.py                                              :+:    :+: :+:    :+: #
#                                                      +:+        +:+          #
#    By: Ser Superior <marcioeduine@gmail.com>        +#++:++#++ +#++:++#++    #
#                                                        +#+        +#+        #
#    Created: 2026/07/09 10:25:00 by Ser Superior   #+#    #+# #+#    #+#        #
#    Updated: 2026/07/15 21:26:00 by Ser Superior  ########   ########         #
#                                                                              #
# **************************************************************************** #
"""REPL entry point: input analysis, command dispatching, and main loop.

The SS_DB Engine now operates as a unified multi-engine client.
All original custom commands are preserved and function identically.
New session commands: connect, use, sessions, disconnect.
"""

import sys
import shlex

from utils import initialise_cli_history
from session_manager import SessionManager
from config_commands import handle_config_command, handle_help_command
from schema_commands import (
    handle_open_command,
    handle_list_ls_command,
    handle_print_command,
    handle_inspect_command,
    handle_schema_dot_command,
)
from export_commands import handle_export_command
from data_commands import handle_update_command, handle_rename_command, handle_insert_command
from sql_engine import handle_raw_sql


def _get_active_or_warn(session_manager: SessionManager) -> object:
    """Return the active session, or print a warning and return None."""
    session = session_manager.get_active_session()
    if not session:
        print(
            "Error: No active database session. "
            "Use 'connect <alias> <connection_string>' to open one."
        )
    return session


def main() -> None:
    session_manager = SessionManager()

    engine_config = {
        "echo": False,
        "timer": False,
        "eqp": False,
        "stats": False,
        "in_transaction": False
    }

    initialise_cli_history()

    # ------------------------------------------------------------------ #
    # Bootstrap: if a path/URI is supplied as a CLI argument, open it      #
    # automatically under the alias 'default'.                             #
    # ------------------------------------------------------------------ #
    if len(sys.argv) > 1:
        initial_target = sys.argv[1]
        if not session_manager.register_connection("default", initial_target):
            print("Warning: Initial connection failed. Starting without an active session.")
        else:
            print("Optimisation profiles loaded. Enter 'config' or 'help' to audit system state.")
    else:
        print("SS_DB Engine started. No session active.")
        print(
            "Use 'connect <alias> <connection_string>' to open a database,\n"
            "or 'connect local :memory:' for a transient in-memory workspace.\n"
        )
        print("Optimisation profiles loaded. Enter 'config' or 'help' to audit system state.")

    # ------------------------------------------------------------------ #
    # Main REPL loop                                                       #
    # ------------------------------------------------------------------ #
    while True:
        session = session_manager.get_active_session()
        tx_active = engine_config["in_transaction"]
        prompt = session_manager.build_prompt(tx_active)

        try:
            user_input = input(prompt).strip()
        except (KeyboardInterrupt, EOFError):
            print("\nShutting down engine gracefully...")
            break

        if not user_input:
            continue

        try:
            parts = shlex.split(user_input)
        except ValueError as lex_error:
            print(f"Lexer Error: {lex_error}")
            continue

        if not parts:
            continue

        cmd = parts[0].lower()

        # -------------------------------------------------------------- #
        # Universal commands (no active session required)                  #
        # -------------------------------------------------------------- #

        if cmd in ("exit", "quit"):
            break

        elif cmd == "help":
            handle_help_command()

        elif cmd in ("clear", "cl"):
            print("\033[H\033[2J", end="")

        elif cmd in ("config", "settings", "configuration", "conf"):
            db_label = session.db_name if session else ":none:"
            handle_config_command(db_label, parts, engine_config)

        # -------------------------------------------------------------- #
        # Session management commands                                      #
        # -------------------------------------------------------------- #

        elif cmd == "connect":
            # Usage: connect <alias> <connection_string>
            if len(parts) < 3:
                print("Error: Missing arguments. Usage: connect <alias> <connection_string>")
                continue
            alias = parts[1]
            conn_string = parts[2]
            session_manager.register_connection(alias, conn_string)

        elif cmd == "use":
            # Usage: use <alias>
            if len(parts) < 2:
                print("Error: Missing alias. Usage: use <alias>")
                continue
            session_manager.switch_session(parts[1])
            # Reset table context when switching sessions
            engine_config["in_transaction"] = False

        elif cmd in ("sessions", "connections"):
            session_manager.list_sessions()

        elif cmd == "disconnect":
            # Usage: disconnect <alias>
            if len(parts) < 2:
                print("Error: Missing alias. Usage: disconnect <alias>")
                continue
            session_manager.disconnect_session(parts[1])
            engine_config["in_transaction"] = False

        # -------------------------------------------------------------- #
        # Legacy .dbload: re-implemented as a session shortcut             #
        # Loads a new SQLite file into the 'default' session slot.         #
        # -------------------------------------------------------------- #
        elif cmd == ".dbload":
            if len(parts) < 2:
                print("Error: Missing target path. Usage: .dbload <database_name.db>")
                continue

            new_db = parts[1]

            # Disconnect 'default' if it exists, then re-connect
            if "default" in session_manager.sessions:
                session_manager.sessions["default"].driver.disconnect()
                del session_manager.sessions["default"]

            registered = session_manager.register_connection("default", new_db)
            if registered:
                session_manager.active_alias = "default"
                # Clear the table context in the new session
                new_session = session_manager.get_active_session()
                if new_session:
                    new_session.active_table = None
                engine_config["in_transaction"] = False
                print(f"Successfully shifted database execution scope to: [{new_db}]")
            else:
                print("Falling back to a transient in-memory safe-net workspace.")
                session_manager.register_connection("default", ":memory:")
                session_manager.active_alias = "default"
                engine_config["in_transaction"] = False
            continue

        # -------------------------------------------------------------- #
        # All commands below require an active session                     #
        # -------------------------------------------------------------- #

        elif cmd == "open":
            session = _get_active_or_warn(session_manager)
            if not session:
                continue
            result = handle_open_command(session.driver, parts)
            if result:
                session.active_table = result

        elif cmd == "close":
            session = _get_active_or_warn(session_manager)
            if not session:
                continue
            if session.active_table:
                session.active_table = None
            else:
                print("Error: No active table context to close.")

        elif cmd in ("list", "ls"):
            session = _get_active_or_warn(session_manager)
            if not session:
                continue
            handle_list_ls_command(session.driver, session.active_table, parts)

        elif cmd == "print":
            session = _get_active_or_warn(session_manager)
            if not session:
                continue
            handle_print_command(session.driver, session.active_table, parts)

        elif cmd in ("inspect", "audit"):
            session = _get_active_or_warn(session_manager)
            if not session:
                continue
            handle_inspect_command(session.driver, session.active_table, parts)

        elif cmd == ".schema":
            session = _get_active_or_warn(session_manager)
            if not session:
                continue
            handle_schema_dot_command(session.driver, session.active_table, parts)

        elif cmd == "export":
            session = _get_active_or_warn(session_manager)
            if not session:
                continue
            handle_export_command(session.driver, parts)

        elif cmd == "update":
            session = _get_active_or_warn(session_manager)
            if not session:
                continue
            # Route ANSI SQL 'UPDATE <table> SET' directly to the raw engine
            if len(parts) > 2 and parts[2].lower() == "set":
                handle_raw_sql(
                    session.driver.connection,
                    session.driver.cursor,
                    session.db_name,
                    user_input,
                    engine_config
                )
            else:
                handle_update_command(
                    session.driver.connection,
                    session.driver.cursor,
                    session.active_table,
                    parts,
                    engine_config
                )

        elif cmd == "rename":
            session = _get_active_or_warn(session_manager)
            if not session:
                continue
            new_table = handle_rename_command(
                session.driver.connection,
                session.driver.cursor,
                session.active_table,
                parts,
                engine_config
            )
            session.active_table = new_table

        elif cmd == "insert":
            session = _get_active_or_warn(session_manager)
            if not session:
                continue
            # Route ANSI SQL 'INSERT INTO ...' directly to the raw engine
            if len(parts) > 1 and parts[1].lower() == "into":
                handle_raw_sql(
                    session.driver.connection,
                    session.driver.cursor,
                    session.db_name,
                    user_input,
                    engine_config
                )
            else:
                handle_insert_command(
                    session.driver.connection,
                    session.driver.cursor,
                    session.active_table,
                    parts,
                    engine_config
                )

        elif cmd == "begin":
            if engine_config["in_transaction"]:
                print("Warning: A transaction block is already active.")
            else:
                engine_config["in_transaction"] = True
                print("Transaction started. Structural locks are now active.")

        elif cmd == "commit":
            if not engine_config["in_transaction"]:
                print("Warning: No active transaction block discovered to commit.")
            else:
                session = _get_active_or_warn(session_manager)
                if not session:
                    continue
                session.driver.connection.commit()
                engine_config["in_transaction"] = False
                print("Transaction successfully committed to disk storage.")

        elif cmd == "rollback":
            if not engine_config["in_transaction"]:
                print("Warning: No active transaction block discovered to roll back.")
            else:
                session = _get_active_or_warn(session_manager)
                if not session:
                    continue
                session.driver.connection.rollback()
                engine_config["in_transaction"] = False
                print("Transaction rolled back successfully. Changes discarded.")

        else:
            session = _get_active_or_warn(session_manager)
            if not session:
                continue
            handle_raw_sql(
                session.driver.connection,
                session.driver.cursor,
                session.db_name,
                user_input,
                engine_config
            )

    # ------------------------------------------------------------------ #
    # Graceful shutdown: disconnect all registered sessions                #
    # ------------------------------------------------------------------ #
    for alias in list(session_manager.sessions.keys()):
        session_manager.sessions[alias].driver.disconnect()


if __name__ == "__main__":
    main()

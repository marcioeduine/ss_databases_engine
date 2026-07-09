#!/usr/bin/env python3
# **************************************************************************** #
#                                                                              #
#                                                        ::::::::   ::::::::   #
#    cli.py                                            :+:    :+: :+:    :+:   #
#                                                     +:+        +:+           #
#    By: Ser Superior <marcioeduine@gmail.com>       +#++:++#++ +#++:++#++     #
#                                                          +#+        +#+      #
#    Created: 2026/07/09 10:25:00 by Ser Superior  #+#    #+# #+#    #+#       #
#    Updated: 2026/07/09 21:50:00 by Ser Superior  ########   ########         #
#                                                                              #
# **************************************************************************** #
"""REPL entry point: input analysis, command dispatching, and main loop."""

import sqlite3
import sys
import shlex

from utils import initialise_cli_history
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


def main() -> None:
    # Fallback to an isolated transient in-memory workspace if no file argument is provided
    db_name = sys.argv[1] if len(sys.argv) > 1 else ":memory:"
    
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
    except Exception as error:
        print(f"[ ERROR ] Database infrastructure initialisation failed: {error}")
        sys.exit(1)

    engine_config = {
        "echo": False,
        "timer": False,
        "eqp": False,
        "stats": False,
        "in_transaction": False
    }

    initialise_cli_history()
    current_table = None

    if db_name == ":memory:":
        print("Connected to a transient in-memory database.")
        print("Use '.dbload <database_name.db>' to bind a persistent storage layer.\n")
    else:
        print(f"SS SSQLite connected natively to physical storage: [{db_name}]")
    
    print("Optimisation profiles loaded. Enter 'config' or 'help' to audit system state.")

    while True:
        tx_status = " [TX ACTIVE]" if engine_config["in_transaction"] else ""
        prompt = f"SS_SQL3 ({current_table}){tx_status}> " if current_table else f"SS_SQL3{tx_status}> "

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

        if cmd in ("exit", "quit"):
            break
        elif cmd == "help":
            handle_help_command()
        elif cmd in ("clear", "cl"):
            print("\033[H\033[2J", end="")
        elif cmd in ("config", "settings", "configuration", "conf"):
            handle_config_command(db_name, parts, engine_config)
            
        # Implementing the runtime database attachment pipeline
        elif cmd == ".dbload":
            if len(parts) < 2:
                print("Error: Missing target path. Usage: .dbload <database_name.db>")
                continue
            
            new_db = parts[1]
            try:
                # Safely terminate the current operational database connection descriptors
                conn.close()
                
                # Bind the operational infrastructure to the new physical binary targets
                conn = sqlite3.connect(new_db)
                cursor = conn.cursor()
                db_name = new_db
                current_table = None  # Clear active metadata context on switch
                engine_config["in_transaction"] = False
                print(f"Successfully shifted database execution scope to: [{db_name}]")
            except Exception as context_error:
                print(f"Error: Runtime database attachment aborted: {context_error}")
                print("Falling back to a transient in-memory safe-net workspace.")
                conn = sqlite3.connect(":memory:")
                cursor = conn.cursor()
                db_name = ":memory:"
                current_table = None
                engine_config["in_transaction"] = False
            continue

        elif cmd == "open":
            result = handle_open_command(cursor, parts)
            if result:
                current_table = result
        elif cmd == "close":
            if current_table:
                current_table = None
            else:
                print("Error: No active table context to close.")
        elif cmd in ("list", "ls"):
            handle_list_ls_command(cursor, current_table, parts)
        elif cmd == "print":
            handle_print_command(cursor, current_table, parts)
        elif cmd in ("inspect", "audit"):
            handle_inspect_command(cursor, current_table, parts)
        elif cmd == ".schema":
        	handle_schema_dot_command(cursor, current_table, parts)
        elif cmd == "export":
            handle_export_command(cursor, parts)
        elif cmd == "update":
            handle_update_command(conn, cursor, current_table, parts, engine_config)
        elif cmd == "rename":
            current_table = handle_rename_command(conn, cursor, current_table, parts, engine_config)
        elif cmd == "insert":
            handle_insert_command(conn, cursor, current_table, parts, engine_config)
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
                conn.commit()
                engine_config["in_transaction"] = False
                print("Transaction successfully committed to disk storage.")
        elif cmd == "rollback":
            if not engine_config["in_transaction"]:
                print("Warning: No active transaction block discovered to roll back.")
            else:
                conn.rollback()
                engine_config["in_transaction"] = False
                print("Transaction rolled back successfully. Changes discarded.")
        else:
            handle_raw_sql(conn, cursor, db_name, user_input, engine_config)

    conn.close()


if __name__ == "__main__":
    main()

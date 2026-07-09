#!/usr/bin/env python3
# **************************************************************************** #
#                                                                              #
#                                                        ::::::::   ::::::::   #
#    schema_commands.py                                :+:    :+: :+:    :+:   #
#                                                     +:+        +:+           #
#    By: Ser Superior <marcioeduine@gmail.com>       +#++:++#++ +#++:++#++     #
#                                                          +#+        +#+      #
#    Created: 2026/07/09 10:25:00 by Ser Superior  #+#    #+# #+#    #+#       #
#    Updated: 2026/07/09 20:22:00 by Ser Superior  ########   ########         #
#                                                                              #
# **************************************************************************** #
"""Comandos de navegação e inspecção do esquema: open, close, list, print, inspect."""

import sqlite3

from utils import print_tabular_output

def handle_schema_dot_command(cursor: sqlite3.Cursor, current_table: str or None, parts: list) -> None:
    """Extracts and displays the native DDL creation statement for the targeted entity."""
    if len(parts) > 1:
        target_table = parts[1]
    elif current_table:
        target_table = current_table
    else:
        print("Error: Specify a target table or open a table context first. Usage: .schema <table_name>")
        return

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (target_table,))
    if not cursor.fetchone():
        print(f"Error: Table '{target_table}' does not exist in the active schema.")
        return

    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?;", (target_table,))
    result = cursor.fetchone()
    if result and result[0]:
        print(f"\n{result[0]};")

def handle_open_command(cursor: sqlite3.Cursor, parts: list) -> str or None:
    """Validates and switches context into the specified table schema."""
    if len(parts) < 2:
        print("Error: Target table must be specified. Example: open ss_evento")
        return None
    target_table = parts[1]
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (target_table,))
    if cursor.fetchone():
        return target_table
    print(f"Error: Table '{target_table}' does not exist in the active schema.")
    return None


def handle_list_ls_command(cursor: sqlite3.Cursor, current_table: str or None, parts: list) -> None:
    """Handles schema lookup commands natively while respecting lexical jurisdiction."""
    headers = ["cid", "name", "type", "notnull", "dflt_value", "pk"]
    if current_table:
        cursor.execute(f"PRAGMA table_info({current_table});")
        print_tabular_output(headers, cursor.fetchall())
    else:
        if len(parts) == 1:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            print_tabular_output(["Available Tables Context"], cursor.fetchall())
        else:
            target_table = parts[1]
            cursor.execute(f"PRAGMA table_info({target_table});")
            print_tabular_output(headers, cursor.fetchall())


def handle_print_command(cursor: sqlite3.Cursor, current_table: str or None, parts: list) -> None:
    """Dumps targeted row contents dynamically supporting N-column projections."""
    if not current_table:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        print_tabular_output(["Available Tables Context"], cursor.fetchall())
    else:
        if len(parts) == 1:
            cursor.execute(f"SELECT * FROM {current_table};")
            headers = [description[0] for description in cursor.description]
            print_tabular_output(headers, cursor.fetchall())
        else:
            target_columns = parts[1:]
            try:
                cursor.execute(f"SELECT {', '.join(target_columns)} FROM {current_table};")
                print_tabular_output(target_columns, cursor.fetchall())
            except sqlite3.OperationalError as error:
                print(f"SQL Error: {error}")


def handle_inspect_command(cursor: sqlite3.Cursor, current_table: str or None, parts: list) -> None:
    """Audits hidden operational metadata structures like indexes and foreign constraints."""
    if len(parts) > 1:
        target_table = parts[1]
    elif current_table:
        target_table = current_table
    else:
        print("Error: Specify a target table or open a table context first. Usage: inspect <table_name>")
        return
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (target_table,))
    if not cursor.fetchone():
        print(f"Error: Table '{target_table}' does not exist in the active schema.")
        return
    print(f"\n=== Deep Architectural Inspection Profile: [{target_table}] ===")
    try:
        cursor.execute(f"PRAGMA index_list({target_table});")
        indexes = cursor.fetchall()
        if not indexes:
            print("  Indexes     : No database indexes mapped to this entity.")
        else:
            print("  Indexes     :")
            for idx in indexes:
                is_unique = "UNIQUE" if idx[2] == 1 else "STANDARD"
                print(f"    - Name: {idx[1]} | Type: {is_unique}")
    except Exception as error:
        print(f"  Index audit failed: {error}")

    try:
        cursor.execute(f"PRAGMA foreign_key_list({target_table});")
        f_keys = cursor.fetchall()
        if not f_keys:
            print("  Foreign Keys: No external foreign constraints discovered.")
        else:
            print("  Foreign Keys:")
            for fk in f_keys:
                print(f"    - Column [{fk[3]}] references Parent Table [{fk[2]}] column ({fk[4]})")
    except Exception as error:
        print(f"  Foreign key audit failed: {error}")
    print("==================================================================\n")

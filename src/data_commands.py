#!/usr/bin/env python3
# **************************************************************************** #
#                                                                              #
#                                                        ::::::::   ::::::::   #
#    data_commands.py                                  :+:    :+: :+:    :+:   #
#                                                     +:+        +:+           #
#    By: Ser Superior <marcioeduine@gmail.com>       +#++:++#++ +#++:++#++     #
#                                                          +#+        +#+      #
#    Created: 2026/07/09 10:25:00 by Ser Superior  #+#    #+# #+#    #+#       #
#    Updated: 2026/07/10 14:35:00 by Ser Superior  ########   ########         #
#                                                                              #
# **************************************************************************** #
"""Comandos de manipulação estrutural e de registos: update, rename, insert."""

import sqlite3


def handle_update_command(conn: sqlite3.Connection, cursor: sqlite3.Cursor, current_table: str or None, parts: list, engine_config: dict) -> None:
    """Updates a targeted column value bounded by ID inside the active table context."""
    if not current_table:
        print("Error: Active table context required. Execute 'open [table]' first.")
        return
    if len(parts) < 4:
        print("Error: Invalid syntax. Usage: update <column> <id> <new_value>")
        return
    column = parts[1]
    row_id = parts[2]
    new_value = parts[3]
    try:
        query = f"UPDATE {current_table} SET {column} = ? WHERE id = ?;"
        cursor.execute(query, (new_value, row_id))
        if not engine_config["in_transaction"]:
            conn.commit()
        print(f"Success: Table '{current_table}' column '{column}' updated for ID {row_id}.")
    except Exception as error:
        print(f"Update record compilation collapsed: {error}")


def handle_rename_command(conn: sqlite3.Connection, cursor: sqlite3.Cursor, current_table: str or None, parts: list, engine_config: dict) -> str or None:
    """Executes dynamic renames for tables or columns based on context arguments."""
    args_count = len(parts) - 1
    if args_count < 1:
        print("Error: Invalid syntax for 'rename' macro command.")
        return current_table

    if current_table:
        if args_count == 1:
            new_table_name = parts[1]
            try:
                cursor.execute(f"ALTER TABLE {current_table} RENAME TO {new_table_name};")
                if not engine_config["in_transaction"]:
                    conn.commit()
                print(f"Table '{current_table}' successfully renamed to '{new_table_name}'.")
                return new_table_name
            except sqlite3.OperationalError as error:
                print(f"SQL Error: {error}")
                return current_table
        elif args_count == 2:
            old_col = parts[1]
            new_col = parts[2]
            try:
                cursor.execute(f"ALTER TABLE {current_table} RENAME COLUMN {old_col} TO {new_col};")
                if not engine_config["in_transaction"]:
                    conn.commit()
                print(f"Column '{old_col}' successfully renamed to '{new_col}' inside table '{current_table}'.")
            except sqlite3.OperationalError as error:
                print(f"SQL Error: {error}")
            return current_table
        else:
            print("Error: Excessive arguments for 'rename' command inside a table context.")
            return current_table
    else:
        if args_count == 2:
            old_table = parts[1]
            new_table = parts[2]
            try:
                cursor.execute(f"ALTER TABLE {old_table} RENAME TO {new_table};")
                if not engine_config["in_transaction"]:
                    conn.commit()
                print(f"Table '{old_table}' successfully renamed to '{new_table}'.")
            except sqlite3.OperationalError as error:
                print(f"SQL Error: {error}")
            return None
        elif args_count == 3:
            table_target = parts[1]
            old_col = parts[2]
            new_col = parts[3]
            try:
                cursor.execute(f"ALTER TABLE {table_target} RENAME COLUMN {old_col} TO {new_col};")
                if not engine_config["in_transaction"]:
                    conn.commit()
                print(f"Column '{old_col}' successfully renamed to '{new_col}' inside table '{table_target}'.")
            except sqlite3.OperationalError as error:
                print(f"SQL Error: {error}")
            return None
        else:
            print("Error: Invalid argument layout for root space 'rename'.")
            return None


def handle_insert_command(conn: sqlite3.Connection, cursor: sqlite3.Cursor, current_table: str or None, parts: list, engine_config: dict) -> None:
    """Handles dynamic, type-safe row insertions for any active table context."""
    if not current_table:
        print("Error: Active table context required. Execute 'open [table]' first.")
        return

    args = parts[1:]
    try:
        # Audit the template table 'original' to extract preferred structural column ordering
        try:
            cursor.execute("PRAGMA table_info(original);")
            orig_info = cursor.fetchall()
            orig_insert_columns = []
            for col in orig_info:
                is_pk = col[5] == 1
                col_type = col[2].upper()
                if is_pk and ("INT" in col_type or col_type == ""):
                    continue
                orig_insert_columns.append(col[1])
        except Exception:
            orig_insert_columns = []

        cursor.execute(f"PRAGMA table_info({current_table});")
        columns_info = cursor.fetchall()
        curr_columns = [col[1] for col in columns_info]

        # Realign insertion targets if current entity matches template columns layout
        if orig_insert_columns and set(orig_insert_columns).issubset(set(curr_columns)):
            insert_columns = orig_insert_columns
        else:
            insert_columns = []
            for col in columns_info:
                is_pk = col[5] == 1
                col_type = col[2].upper()
                if is_pk and ("INT" in col_type or col_type == ""):
                    continue
                insert_columns.append(col[1])

        if len(args) != len(insert_columns):
            print(f"Error: Match failure. Expected {len(insert_columns)} fields, got {len(args)}.")
            return

        processed_args = []
        for val in args:
            if val.lower() == "null":
                processed_args.append(None)
            elif val.isdigit():
                processed_args.append(int(val))
            else:
                processed_args.append(val)

        placeholders = ", ".join(["?"] * len(insert_columns))
        query = f"INSERT INTO {current_table} ({', '.join(insert_columns)}) VALUES ({placeholders});"
        cursor.execute(query, processed_args)
        if not engine_config["in_transaction"]:
            conn.commit()
        print(f"Row successfully inserted into '{current_table}'.")
    except Exception as error:
        print(f"Insertion failed: {error}")

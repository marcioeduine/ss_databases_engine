#!/usr/bin/env python3
# **************************************************************************** #
#                                                                              #
#                                                        ::::::::   ::::::::   #
#    sql_engine.py                                     :+:    :+: :+:    :+:   #
#                                                     +:+        +:+           #
#    By: Ser Superior <marcioeduine@gmail.com>       +#++:++#++ +#++:++#++     #
#                                                          +#+        +#+      #
#    Created: 2026/07/09 10:25:00 by Ser Superior  #+#    #+# #+#    #+#       #
#    Updated: 2026/07/09 21:10:00 by Ser Superior  ########   ########         #
#                                                                              #
# **************************************************************************** #
"""Raw SQL execution core engine featuring character-aware multi-statement parsing streams."""

import sqlite3
import time

from utils import print_tabular_output, get_database_weight


def handle_raw_sql(conn: sqlite3.Connection, cursor: sqlite3.Cursor, db_name: str, user_input: str, engine_config: dict) -> None:
    """Parses and executes standard ANSI SQL queries with embedded performance profiling hooks."""
    if engine_config["echo"]:
        print(f"[ECHO] Intercepted input stream: {user_input}")

    # Extract multiple complete SQL statements safely without splitting internal string literal semicolons
    statements = []
    current_accumulator = []
    
    for char in user_input:
        current_accumulator.append(char)
        if char == ';':
            candidate_string = "".join(current_accumulator)
            if sqlite3.complete_statement(candidate_string):
                statements.append(candidate_string.strip())
                current_accumulator = []
                
    remainder_string = "".join(current_accumulator).strip()
    if remainder_string:
        statements.append(remainder_string)

    # Process extracted structured statements sequentially inside the database connection pipeline
    for statement_stripped in statements:
        if not statement_stripped:
            continue

        upper_input = statement_stripped.upper()

        if engine_config["eqp"] and (upper_input.startswith("SELECT") or upper_input.startswith("WITH")):
            print("\n--- [EQP] Query Compilation Mapping Plan ---")
            try:
                cursor.execute(f"EXPLAIN QUERY PLAN {statement_stripped}")
                eqp_headers = [desc[0] for desc in cursor.description]
                print_tabular_output(eqp_headers, cursor.fetchall())
                print("---------------------------------------------\n")
            except Exception as eqp_error:
                print(f"[EQP Profiler Error] Execution compilation collapsed: {eqp_error}")

        start_timestamp = time.perf_counter()
        try:
            cursor.execute(statement_stripped)
            has_results = cursor.description is not None
            if has_results:
                headers = [description[0] for description in cursor.description]
                rows = cursor.fetchall()
            else:
                rows = []
        except Exception as error:
            print(f"SQL Error: {error}")
            return
        end_timestamp = time.perf_counter()

        if has_results:
            print_tabular_output(headers, rows)

        if engine_config["timer"]:
            elapsed_delta = end_timestamp - start_timestamp
            print(f"\n[TIMER] Engine processing resolution delta: {elapsed_delta:.6f} seconds")

        if engine_config["stats"]:
            print("\n--- [STATS] Structural Engine Metaspace Telemetry ---")
            print(f"  Rows Transferred / Altered: {len(rows) if has_results else cursor.rowcount}")
            try:
                cursor.execute("PRAGMA page_count;")
                page_count = cursor.fetchone()[0]
                cursor.execute("PRAGMA page_size;")
                page_size = cursor.fetchone()[0]
                cursor.execute("PRAGMA freelist_count;")
                freelist_count = cursor.fetchone()[0]

                print(f"  Active Allocation Page Count: {page_count}")
                print(f"  Low-Level Page Size Footprint: {page_size} Bytes")
                print(f"  Available Freelist Page Slots: {freelist_count}")
                print(f"  Absolute Virtual File Weight : {get_database_weight(db_name)}")
            except Exception as stats_error:
                print(f"[Telemetry Error] Metadata generation missing: {stats_error}")
            print("-----------------------------------------------------\n")

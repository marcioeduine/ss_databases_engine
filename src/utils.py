#!/usr/bin/env python3
# **************************************************************************** #
#                                                                              #
#                                                        ::::::::   ::::::::   #
#    utils.py                                          :+:    :+: :+:    :+:   #
#                                                     +:+        +:+           #
#    By: Ser Superior <marcioeduine@gmail.com>       +#++:++#++ +#++:++#++     #
#                                                          +#+        +#+      #
#    Created: 2026/07/09 10:25:00 by Ser Superior  #+#    #+# #+#    #+#       #
#    Updated: 2026/07/09 20:22:00 by Ser Superior  ########   ########         #
#                                                                              #
# **************************************************************************** #
"""Funções transversais: histórico do CLI, peso da BD e impressão tabular."""

import os
import readline
import atexit

# Unique system environment history file path binding
HISTORY_FILE = os.path.expanduser("~/.ss_sqlite_history")


def initialise_cli_history() -> None:
    """Initialises persistent operational command histories into active memory space."""
    if os.path.exists(HISTORY_FILE):
        try:
            readline.read_history_file(HISTORY_FILE)
        except IOError:
            print("Warning: Persistent history pipeline was unable to resolve memory files.")
    atexit.register(readline.write_history_file, HISTORY_FILE)


def get_database_weight(db_name: str) -> str:
    """Computes the raw binary file size profile of the targeted database."""
    if not os.path.exists(db_name):
        return "0 Bytes"
    size_bytes = os.path.getsize(db_name)
    if size_bytes < 1024:
        return f"{size_bytes} Bytes"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


def print_tabular_output(headers: list, rows: list) -> None:
    """Computes dynamic column padding and displays database records natively."""
    if not headers:
        return
    string_rows = [[str(item) if item is not None else "NULL" for item in row] for row in rows]
    col_widths = [len(h) for h in headers]
    for row in string_rows:
        for idx, item in enumerate(row):
            if len(item) > col_widths[idx]:
                col_widths[idx] = len(item)
    header_line = "  ".join(f"{headers[idx]:<{col_widths[idx]}}" for idx in range(len(headers)))
    print(header_line)
    separator_line = "  ".join("-" * col_widths[idx] for idx in range(len(col_widths)))
    print(separator_line)
    for row in string_rows:
        data_line = "  ".join(f"{row[idx]:<{col_widths[idx]}}" for idx in range(len(row)))
        print(data_line)

#!/usr/bin/env python3
# **************************************************************************** #
#                                                                              #
#                                                        ::::::::   ::::::::   #
#    config_commands.py                                :+:    :+: :+:    :+:   #
#                                                     +:+        +:+           #
#    By: Ser Superior <marcioeduine@gmail.com>       +#++:++#++ +#++:++#++     #
#                                                          +#+        +#+      #
#    Created: 2026/07/09 10:25:00 by Ser Superior  #+#    #+# #+#    #+#       #
#    Updated: 2026/07/09 20:22:00 by Ser Superior  ########   ########         #
#                                                                              #
# **************************************************************************** #
"""Comandos de telemetria/configuração do motor e menu de ajuda."""

from utils import get_database_weight


def handle_config_command(db_name: str, parts: list, engine_config: dict) -> None:
    """Manages telemetry parameters and inspection profiles for database evaluation."""
    if len(parts) == 1:
        print(f"\n--- SSSQLite Engine Configuration Status [{db_name}] ---")
        print(f"  echo   (Statement Echoing)       : {'ON' if engine_config['echo'] else 'OFF'}")
        print(f"  timer  (Execution Profiler)      : {'ON' if engine_config['timer'] else 'OFF'}")
        print(f"  eqp    (Explain Query Plan)      : {'ON' if engine_config['eqp'] else 'OFF'}")
        print(f"  stats  (Low-Level DB Telemetry)  : {'ON' if engine_config['stats'] else 'OFF'}")
        print(f"  [Disk Weight/Allocation]         : {get_database_weight(db_name)}")
        print("-----------------------------------------------------------------\n")
        return
    if len(parts) < 3:
        print("Error: Invalid syntax. Usage: config <option_name> <on/off>")
        return
    target_option = parts[1].lower()
    target_value = parts[2].lower()
    if target_option not in engine_config or target_option == "in_transaction":
        print(f"Error: Internal runtime profile does not recognize target option '{target_option}'.")
        return
    if target_value in ("on", "true", "1"):
        engine_config[target_option] = True
        print(f"Configuration option '{target_option}' successfully enabled.")
    elif target_value in ("off", "false", "0"):
        engine_config[target_option] = False
        print(f"Configuration option '{target_option}' successfully disabled.")
    else:
        print(f"Error: Unrecognized operational assignment token '{target_value}'. Use 'on' or 'off'.")


def handle_help_command() -> None:
    """Displays the custom help menu mapping available macro actions."""
    print("\nSS SSQLite (SSSQLite) Custom Macro Commands:")
    print("  help                               - Displays this operational guidance menu.")
    print("  clear / cl                         - Clears the terminal screen interface.")
    print("  config / settings / conf           - Displays database file metrics and runtime telemetry profiles.")
    print("  config <option> <on/off>           - Toggles operational modes (options: echo, timer, eqp, stats).")
    print("  open <table_name>                  - Opens and locks context into the target table.")
    print("  close                              - Closes the active table context, returning to root.")
    print("  list / ls                          - Lists all tables (root) or all columns of the active table.")
    print("  print                              - Lists all tables (root) or prints all row records (inside table).")
    print("  inspect / audit                    - Audits structural indexes and foreign keys of active table.")
    print("  inspect / audit <table_name>       - Audits structural indexes and foreign keys of targeted table.")
    print("  export <csv/json/pdf> <file> <src> - Serialises a table or raw query results directly to disk.")
    print("  update <col> <id> <new_val>        - Updates a row value by ID inside the active table context.")
    print("  rename <old_table> <new_table>     - Structural operational entity renamer macro.")
    print("  insert <args...>                   - Dynamic row insertion macro (supports '', \"\" and NULL).")
    print("  begin                              - Explicitly starts a safe transaction boundary block.")
    print("  commit                             - Natively commits all structural changes onto disk storage.")
    print("  rollback                           - Discards all execution modifications inside active transaction.")
    print("  exit / quit                        - Gracefully terminates the interpreter instance.\n")

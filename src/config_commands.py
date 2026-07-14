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
"""Engine telemetry/configuration commands and the built-in help menu."""

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
    print("\nSS_DB Engine — Custom Macro Commands:")
    print("")
    print("  SESSION MANAGEMENT")
    print("  ------------------")
    print("  connect <alias> <conn_string>      - Open and register a new database session under a named alias.")
    print("    Examples:  connect local database.db")
    print("               connect prod postgresql://user:pass@host/dbname")
    print("               connect mem :memory:")
    print("  use <alias>                        - Switch active operational focus to the named session.")
    print("  sessions / connections             - List all registered sessions and their current state.")
    print("  disconnect <alias>                 - Close and remove the named session from the registry.")
    print("  .dbload <database_name.db>         - Shortcut: reload the 'default' session with a new SQLite file.")
    print("")
    print("  PROMPT FORMAT")
    print("  -------------")
    print("  SS_DB [type::alias] (table)>       - Prompt reflects active engine type, session alias, and table.")
    print("")
    print("  NAVIGATION & INSPECTION")
    print("  -----------------------")
    print("  open <table_name>                  - Open and lock context into the target table or collection.")
    print("  close                              - Close the active table context, returning to session root.")
    print("  list / ls                          - List all tables (root) or all columns of the active table.")
    print("  print                              - List all tables (root) or print all row records (inside table).")
    print("  inspect / audit                    - Audit structural indexes and foreign keys of the active table.")
    print("  inspect / audit <table_name>       - Audit structural indexes and foreign keys of the target table.")
    print("  .schema [table_name]               - Display the native DDL creation statement for the target entity.")
    print("")
    print("  DATA MANIPULATION")
    print("  -----------------")
    print("  insert <args...>                   - Dynamic row insertion macro (supports '', \"\" and NULL).")
    print("  update <col> <id> <new_val>        - Update a row value by ID inside the active table context.")
    print("  rename <old> <new>                 - Rename a table or column (context-aware).")
    print("  export <csv/json/pdf> <file> <src> - Serialise a table or raw query results to disk.")
    print("")
    print("  TRANSACTION CONTROL")
    print("  -------------------")
    print("  begin                              - Explicitly start a safe transaction boundary block.")
    print("  commit                             - Commit all structural changes to persistent storage.")
    print("  rollback                           - Discard all modifications inside the active transaction.")
    print("")
    print("  ENGINE CONFIGURATION")
    print("  --------------------")
    print("  config / settings / conf           - Display database metrics and runtime telemetry profiles.")
    print("  config <option> <on/off>           - Toggle operational modes (options: echo, timer, eqp, stats).")
    print("  clear / cl                         - Clear the terminal screen interface.")
    print("  help                               - Display this operational guidance menu.")
    print("  exit / quit                        - Gracefully terminate the interpreter instance.\n")

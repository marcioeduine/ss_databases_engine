# **************************************************************************** #
#                                                                              #
#                                                        ::::::::   ::::::::   #
#    schema_commands.py                                :+:    :+: :+:    :+:   #
#                                                     +:+        +:+           #
#    By: Ser Superior <marcioeduine@gmail.com>       +#++:++#++ +#++:++#++     #
#                                                          +#+        +#+      #
#    Created: 2026/07/09 10:25:00 by Ser Superior  #+#    #+# #+#    #+#       #
#    Updated: 2026/07/15 21:20:00 by Ser Superior  ########   ########         #
#                                                                              #
# **************************************************************************** #
"""Comandos completos de navegação, inspecção, escrita e transações do SS_DB."""

from utils import print_tabular_output

# --- Comandos de Escrita (Seção 6 do Manual) ---

def handle_update_command(driver, current_table: str or None, parts: list) -> None:
    """update <coluna> <id> <valor>: Actualiza uma linha numa tabela aberta."""
    if not current_table:
        print("Error: No active table context. Use 'open <table_name>' first.")
        return
    if len(parts) < 4:
        print("Usage: update <column> <id> <new_value>")
        return
    
    col, id_val, val = parts[1], parts[2], parts[3]
    if driver.update_record(current_table, col, val, id_val):
        print(f"Table '{current_table}' column '{col}' updated for ID '{id_val}'.")

def handle_insert_command(driver, current_table: str or None, parts: list) -> None:
    """insert <valores>: Insere nova linha na tabela aberta."""
    if not current_table:
        print("Error: No active table context. Use 'open <table_name>' first.")
        return
    values = parts[1:]
    if driver.insert_record(current_table, values):
        print(f"Row successfully inserted into '{current_table}'.")

# --- Comandos de Transação (Seção 9 do Manual) ---

def handle_begin_command(driver) -> None:
    driver.begin_transaction()
    print("Transaction started. Structural locks are now active.")

def handle_commit_command(driver) -> None:
    driver.commit_transaction()
    print("Transaction successfully committed to disk storage.")

def handle_rollback_command(driver) -> None:
    driver.rollback_transaction()
    print("Transaction discarded. State reverted to last known clean point.")

# --- Comandos de Navegação e Inspecção (Seções 4 e 5) ---

def handle_schema_dot_command(driver, current_table: str or None, parts: list) -> None:
    target_table = parts[1] if len(parts) > 1 else current_table
    if not target_table or not driver.entity_exists(target_table):
        print("Error: Invalid table context.")
        return
    print(f"\n{driver.get_table_schema(target_table)};\n")

def handle_open_command(driver, parts: list) -> str or None:
    target = parts[1] if len(parts) > 1 else None
    if target and driver.entity_exists(target):
        return target
    print(f"Error: Context '{target}' does not exist.")
    return None

def handle_list_ls_command(driver, current_table: str or None, parts: list) -> None:
    if current_table:
        headers, rows = driver.fetch_columns_info(current_table)
        print_tabular_output(headers, rows)
    else:
        entities = driver.list_entities()
        print_tabular_output(["Available Contexts (Tables/Views)"], [(e,) for e in entities])

def handle_print_command(driver, current_table: str or None, parts: list) -> None:
    if not current_table:
        print("Error: Use 'open <table_name>' first.")
        return
    headers, rows = driver.fetch_data(current_table, parts[1:] if len(parts) > 1 else None)
    print_tabular_output(headers, rows)

def handle_inspect_command(driver, current_table: str or None, parts: list) -> None:
    target = parts[1] if len(parts) > 1 else current_table
    if not target or not driver.entity_exists(target):
        print("Error: Context does not exist.")
        return
    metadata = driver.inspect_entity(target)
    print(f"\n=== Deep Architectural Inspection Profile: [{target}] ===")
    print(f"Primary Key: {metadata.get('primary_key')}")
    print_tabular_output(["Column", "Type", "Nullable", "Default"], metadata.get('columns', []))

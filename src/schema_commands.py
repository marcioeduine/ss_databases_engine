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
"""Comandos de navegação e inspecção do esquema: open, close, list, print, inspect."""

from utils import print_tabular_output


def handle_schema_dot_command(driver, current_table: str or None, parts: list) -> None:
    """Extracts and displays the native DDL creation statement for the targeted entity."""
    target_table = None
    if len(parts) > 1:
        target_table = parts[1]
    elif current_table:
        target_table = current_table
    else:
        print("Error: Specify a target table or open a table context first. Usage: .schema <table_name>")
        return

    if not driver.entity_exists(target_table):
        print(f"Error: Table or View '{target_table}' does not exist in the active schema.")
        return

    ddl_statement = driver.get_table_schema(target_table)
    if ddl_statement:
        print(f"\n{ddl_statement};\n")
    else:
        print(f"Error: DDL extraction not supported or unavailable for '{target_table}'.")


def handle_open_command(driver, parts: list) -> str or None:
    """Validates and switches context into the specified table or view schema."""
    if len(parts) < 2:
        print("Error: Target context must be specified. Example: open dim_players")
        return None
        
    target_table = parts[1]
    if driver.entity_exists(target_table):
        return target_table
        
    print(f"Error: Context '{target_table}' does not exist in the active schema.")
    return None


def handle_list_ls_command(driver, current_table: str or None, parts: list) -> None:
    """Handles schema lookup commands dynamically through the active driver abstraction layer."""
    if current_table:
        headers, rows = driver.fetch_columns_info(current_table)
        if not rows:
            print(f"Error: Metadata for '{current_table}' is unreachable or empty.")
            return
        print_tabular_output(headers, rows)
    else:
        if len(parts) == 1:
            entities = driver.list_entities()
            if not entities:
                print("No entities discovered in the active schema target.")
                return
            
            formatted_rows = [(entity,) for entity in entities]
            print_tabular_output(["Available Contexts (Tables/Views)"], formatted_rows)
        else:
            target_table = parts[1]
            headers, rows = driver.fetch_columns_info(target_table)
            if not rows:
                print(f"Error: Metadata for '{target_table}' is unreachable or empty.")
                return
            print_tabular_output(headers, rows)


def handle_print_command(driver, current_table: str or None, parts: list) -> None:
    """Dumps targeted row contents dynamically supporting N-column projections."""
    if not current_table:
        entities = driver.list_entities()
        formatted_rows = [(entity,) for entity in entities]
        print_tabular_output(["Available Contexts (Tables/Views)"], formatted_rows)
    else:
        target_columns = []
        if len(parts) > 1:
            target_columns = parts[1:]
            
        headers, rows = driver.fetch_data(current_table, target_columns)
        if not headers and not rows:
            print(f"Error: Failed to fetch data from '{current_table}'.")
            return
            
        print_tabular_output(headers, rows)


def handle_inspect_command(driver, current_table: str or None, parts: list) -> None:
    """Audits operational metadata structures like indexes and foreign constraints via driver."""
    target_table = None
    if len(parts) > 1:
        target_table = parts[1]
    elif current_table:
        target_table = current_table
    else:
        print("Error: Specify a target table or open a table context first. Usage: inspect <table_name>")
        return
        
    if not driver.entity_exists(target_table):
        print(f"Error: Context '{target_table}' does not exist in the active schema.")
        return
        
    print(f"\n=== Deep Architectural Inspection Profile: [{target_table}] ===")
    driver.inspect_entity(target_table)
    print("==================================================================\n")

"""
EPC Conversion Utilities

This module contains the EPC generation and conversion logic extracted from the 
original EPC database script, adapted for use in the workflow optimizer application.
"""

import os
import math
import pandas as pd
import openpyxl
from datetime import datetime


def dec_to_bin(value, length):
    """Convert decimal value to binary with specified length."""
    return bin(int(value))[2:].zfill(length)


def bin_to_hex(binary_str):
    """Convert binary string to hexadecimal."""
    hex_str = hex(int(binary_str, 2))[2:].upper()
    return hex_str.zfill(len(binary_str) // 4)


def generate_epc(upc, serial_number):
    """
    Generate EPC hex value from UPC and serial number.
    
    Args:
        upc (str): 12-digit UPC code
        serial_number (int): Serial number
        
    Returns:
        str: EPC hex value
    """
    gs1_company_prefix = "0" + upc[:6]
    item_reference_number = upc[6:11]
    gtin14 = "0" + gs1_company_prefix + item_reference_number
    header = "00110000"
    filter_value = "001"
    partition = "101"
    gs1_binary = dec_to_bin(gs1_company_prefix, 24)
    item_reference_binary = dec_to_bin(item_reference_number, 20)
    serial_binary = dec_to_bin(serial_number, 38)
    epc_binary = header + filter_value + partition + gs1_binary + item_reference_binary + serial_binary
    epc_hex = bin_to_hex(epc_binary)
    return epc_hex


def validate_upc(upc):
    """
    Validate UPC format.
    
    Args:
        upc (str): UPC to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not upc or len(upc) != 12 or not upc.isdigit():
        return False
    return True


def calculate_total_quantity_with_percentages(base_qty, include_2_percent=False, include_7_percent=False):
    """
    Calculate total quantity with optional percentage additions.
    
    Args:
        base_qty (int): Base quantity
        include_2_percent (bool): Whether to add 2% buffer
        include_7_percent (bool): Whether to add 7% buffer
        
    Returns:
        int: Total quantity with percentages applied
    """
    total_qty = int(base_qty)
    if include_2_percent:
        total_qty += int(total_qty * 0.02)
    if include_7_percent:
        total_qty += int(total_qty * 0.07)
    return total_qty


def create_upc_folder_structure(base_path, customer, label_size, po_number, ticket_number, upc, template_base_path=None):
    """
    Create job folder structure following the EPC script pattern:
    base_path/customer/label_size/mm.dd.yy - po_number - ticket_number/upc/[data, print]
    
    Args:
        base_path (str): Base directory path
        customer (str): Customer name
        label_size (str): Label size
        po_number (str): PO number
        ticket_number (str): Ticket number
        upc (str): UPC code
        template_base_path (str): Path to template files (optional)
        
    Returns:
        dict: Dictionary containing created paths
    """
    # Use mm.dd.yy format like the EPC script
    today_date = datetime.now().strftime("%m.%d.%y")
    folder_name = f"{today_date} - {po_number} - {ticket_number}"
    
    # Create directory structure
    job_folder_path = os.path.join(base_path, customer, label_size, folder_name)
    upc_folder_path = os.path.join(job_folder_path, upc)
    print_folder_path = os.path.join(upc_folder_path, "print")
    data_folder_path = os.path.join(upc_folder_path, "data")
    
    # Create all directories
    os.makedirs(print_folder_path, exist_ok=True)
    os.makedirs(data_folder_path, exist_ok=True)
    
    # Copy template if available
    if template_base_path:
        template_path = os.path.join(template_base_path, customer, label_size, f"Template {label_size}.btw")
        if os.path.exists(template_path):
            import shutil
            destination_template = os.path.join(print_folder_path, f"{upc}.btw")
            shutil.copy(template_path, destination_template)
            print(f"Template copied to {destination_template}")
        else:
            print(f"Template not found at {template_path}")
    
    return {
        'job_folder_path': job_folder_path,
        'upc_folder_path': upc_folder_path,
        'print_folder_path': print_folder_path,
        'data_folder_path': data_folder_path,
        'folder_name': folder_name
    }


def generate_epc_database_files(upc, start_serial, total_qty, qty_per_db, save_location):
    """
    Generate EPC database files split into chunks.
    
    Args:
        upc (str): 12-digit UPC
        start_serial (int): Starting serial number
        total_qty (int): Total quantity to generate
        qty_per_db (int): Quantity per database file
        save_location (str): Directory to save files
        
    Returns:
        list: List of created file paths
    """
    if not validate_upc(upc):
        raise ValueError("Invalid UPC format")
    
    end_serial = start_serial + total_qty - 1
    num_serials = end_serial - start_serial + 1
    num_dbs = math.ceil(num_serials / qty_per_db)
    
    created_files = []
    
    for db_index in range(num_dbs):
        chunk_start = start_serial + db_index * qty_per_db
        chunk_end = min(chunk_start + qty_per_db - 1, end_serial)
        chunk_serial_numbers = list(range(chunk_start, chunk_end + 1))
        epc_values = [generate_epc(upc, sn) for sn in chunk_serial_numbers]

        df = pd.DataFrame({
            'UPC': [upc] * len(chunk_serial_numbers),
            'Serial #': chunk_serial_numbers,
            'EPC': epc_values
        })

        start_range = (chunk_start // 1000) + 1 if chunk_start % 1000 == 0 else (chunk_start // 1000)
        end_range = ((chunk_end + 1) // 1000)
        file_name = f"{upc}.DB{db_index + 1}.{start_range}K-{end_range}K.xlsx"
        file_path = os.path.join(save_location, file_name)
        
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
            worksheet = writer.sheets['Sheet1']
            worksheet.column_dimensions['C'].width = 40

        created_files.append(file_path)
    
    return created_files


def generate_epc_preview_data(upc, start_serial, preview_count=10):
    """
    Generate preview data for EPC generation.
    
    Args:
        upc (str): 12-digit UPC
        start_serial (int): Starting serial number
        preview_count (int): Number of rows to preview
        
    Returns:
        pandas.DataFrame: Preview data
    """
    if not validate_upc(upc):
        raise ValueError("Invalid UPC format")
    
    serial_numbers = list(range(start_serial, start_serial + preview_count))
    epc_values = [generate_epc(upc, sn) for sn in serial_numbers]
    
    return pd.DataFrame({
        'UPC': [upc] * len(serial_numbers),
        'Serial #': serial_numbers,
        'EPC': epc_values
    })


def get_template_path(template_base_path, customer, label_size):
    """
    Get the template file path for a given customer and label size.
    
    Args:
        template_base_path (str): Base path for templates
        customer (str): Customer name
        label_size (str): Label size
        
    Returns:
        str: Full path to template file, or None if not found
    """
    template_path = os.path.join(template_base_path, customer, label_size, f"Template {label_size}.btw")
    if os.path.exists(template_path):
        return template_path
    return None


def populate_customer_dropdown_from_templates(template_base_path):
    """
    Get list of customers from template directory structure.
    
    Args:
        template_base_path (str): Base path for templates
        
    Returns:
        list: List of customer names
    """
    if not os.path.exists(template_base_path):
        return []
    
    customers = []
    for item in os.listdir(template_base_path):
        item_path = os.path.join(template_base_path, item)
        if os.path.isdir(item_path):
            customers.append(item)
    
    return sorted(customers)


def populate_label_sizes_for_customer(template_base_path, customer):
    """
    Get list of label sizes for a specific customer from template directory.
    
    Args:
        template_base_path (str): Base path for templates
        customer (str): Customer name
        
    Returns:
        list: List of label sizes for the customer
    """
    customer_path = os.path.join(template_base_path, customer)
    if not os.path.exists(customer_path):
        return []
    
    label_sizes = []
    for item in os.listdir(customer_path):
        item_path = os.path.join(customer_path, item)
        if os.path.isdir(item_path):
            label_sizes.append(item)
    
    return sorted(label_sizes) 
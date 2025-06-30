#!/usr/bin/env python3
"""
Test script for EPC conversion functionality.

This script demonstrates the EPC conversion features integrated from your original
EPC database script into the workflow optimizer application.
"""

import os
import sys
import tempfile
import shutil

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.epc_conversion import (
    validate_upc, generate_epc, generate_epc_preview_data,
    create_upc_folder_structure, generate_epc_database_files,
    calculate_total_quantity_with_percentages
)

def test_epc_generation():
    """Test basic EPC generation functionality."""
    print("=== Testing EPC Generation ===")
    
    # Test UPC validation
    valid_upc = "123456789012"
    invalid_upc = "12345678901"  # Too short
    
    print(f"Validating UPC {valid_upc}: {validate_upc(valid_upc)}")
    print(f"Validating UPC {invalid_upc}: {validate_upc(invalid_upc)}")
    
    # Test EPC generation
    if validate_upc(valid_upc):
        epc1 = generate_epc(valid_upc, 1)
        epc2 = generate_epc(valid_upc, 2)
        print(f"EPC for UPC {valid_upc}, serial 1: {epc1}")
        print(f"EPC for UPC {valid_upc}, serial 2: {epc2}")
    
    print()

def test_preview_generation():
    """Test EPC preview data generation."""
    print("=== Testing EPC Preview Generation ===")
    
    upc = "123456789012"
    start_serial = 1000
    
    try:
        preview_df = generate_epc_preview_data(upc, start_serial, 5)
        print(f"Generated preview data for UPC {upc}, starting at serial {start_serial}:")
        print(preview_df.to_string(index=False))
    except Exception as e:
        print(f"Error generating preview: {e}")
    
    print()

def test_quantity_calculations():
    """Test quantity calculations with buffers."""
    print("=== Testing Quantity Calculations ===")
    
    base_qty = 1000
    
    # Test with no buffers
    total1 = calculate_total_quantity_with_percentages(base_qty, False, False)
    print(f"Base quantity {base_qty}, no buffers: {total1}")
    
    # Test with 2% buffer
    total2 = calculate_total_quantity_with_percentages(base_qty, True, False)
    print(f"Base quantity {base_qty}, 2% buffer: {total2}")
    
    # Test with 7% buffer
    total3 = calculate_total_quantity_with_percentages(base_qty, False, True)
    print(f"Base quantity {base_qty}, 7% buffer: {total3}")
    
    # Test with both buffers
    total4 = calculate_total_quantity_with_percentages(base_qty, True, True)
    print(f"Base quantity {base_qty}, both buffers: {total4}")
    
    print()

def test_folder_structure():
    """Test folder structure creation."""
    print("=== Testing Folder Structure Creation ===")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary directory: {temp_dir}")
        
        # Test parameters
        customer = "Test Customer"
        label_size = "2.9 x 0.47"
        po_number = "PO12345"
        ticket_number = "TK67890"
        upc = "123456789012"
        
        try:
            folder_info = create_upc_folder_structure(
                temp_dir, customer, label_size, po_number, ticket_number, upc
            )
            
            print("Created folder structure:")
            for key, path in folder_info.items():
                exists = "✓" if os.path.exists(path) else "✗"
                print(f"  {key}: {exists} {path}")
                
        except Exception as e:
            print(f"Error creating folder structure: {e}")
    
    print()

def test_database_generation():
    """Test EPC database file generation."""
    print("=== Testing Database File Generation ===")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary directory: {temp_dir}")
        
        upc = "123456789012"
        start_serial = 1000
        total_qty = 2500
        qty_per_db = 1000
        
        try:
            created_files = generate_epc_database_files(
                upc, start_serial, total_qty, qty_per_db, temp_dir
            )
            
            print(f"Generated {len(created_files)} database files:")
            for file_path in created_files:
                size = os.path.getsize(file_path)
                print(f"  {os.path.basename(file_path)} ({size} bytes)")
                
        except Exception as e:
            print(f"Error generating database files: {e}")
    
    print()

def main():
    """Run all tests."""
    print("EPC Conversion Functionality Test")
    print("=" * 50)
    print()
    
    test_epc_generation()
    test_preview_generation()
    test_quantity_calculations()
    test_folder_structure()
    test_database_generation()
    
    print("All tests completed!")

if __name__ == "__main__":
    main() 
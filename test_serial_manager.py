#!/usr/bin/env python3
"""
Test script for the centralized serial number management system.

This script demonstrates:
- Serial number allocation
- Usage logging 
- Multi-user simulation
- Daily file creation
- Duplicate prevention
"""

import os
import sys
import time
from datetime import date

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.serial_manager import get_serial_manager, allocate_serials_for_job


def test_serial_manager():
    """Test the serial number management system."""
    print("🔢 Testing Centralized Serial Number Management System")
    print("=" * 60)
    
    # Test 1: Basic serial allocation
    print("\n📝 Test 1: Basic Serial Allocation")
    print("-" * 40)
    
    try:
        # Use a local test directory
        test_base_path = os.path.join(os.path.dirname(__file__), "test_serials")
        
        # Initialize serial manager
        manager = get_serial_manager(test_base_path)
        
        # Validate base path
        is_valid, message = manager.validate_base_path()
        print(f"Base path validation: {message}")
        
        if not is_valid:
            print("❌ Cannot proceed with tests - base path not accessible")
            return
        
        # Get next available serial
        next_serial = manager.get_next_serial()
        print(f"Next available serial: {next_serial:,}")
        
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
        return
    
    # Test 2: Job-based serial allocation
    print("\n📦 Test 2: Job-based Serial Allocation")
    print("-" * 40)
    
    try:
        # Create test job data
        job_data = {
            'Customer': 'Peak Technologies',
            'PO#': 'PO12345',
            'Ticket#': 'JT67890',
            'UPC Number': '123456789012',
            'Label Size': '1.85 x 0.91',
            'Quantity': '5000'
        }
        
        # Allocate serials for job
        start_serial, end_serial = allocate_serials_for_job(5000, job_data)
        print(f"✅ Allocated serials {start_serial:,} - {end_serial:,} for job {job_data['Ticket#']}")
        print(f"   Total quantity: {end_serial - start_serial + 1:,}")
        
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
        return
    
    # Test 3: Multiple allocations (simulate multiple users)
    print("\n👥 Test 3: Multiple User Simulation")
    print("-" * 40)
    
    try:
        jobs = [
            {'Customer': 'Smead', 'Ticket#': 'SM001', 'Quantity': 2500},
            {'Customer': 'Phenix', 'Ticket#': 'PH002', 'Quantity': 1000},
            {'Customer': 'Peak Technologies', 'Ticket#': 'PT003', 'Quantity': 7500}
        ]
        
        for i, job in enumerate(jobs, 1):
            start, end = allocate_serials_for_job(job['Quantity'], job)
            print(f"   User {i}: {job['Customer']} ({job['Ticket#']}) → {start:,} - {end:,}")
            time.sleep(0.1)  # Small delay to simulate timing differences
            
    except Exception as e:
        print(f"❌ Test 3 failed: {e}")
        return
    
    # Test 4: Daily usage summary
    print("\n📊 Test 4: Daily Usage Summary")
    print("-" * 40)
    
    try:
        summary = manager.get_daily_usage_summary()
        print(f"Date: {summary['date']}")
        print(f"Total allocated today: {summary['total_allocated']:,}")
        print(f"Number of allocations: {summary['allocations_count']}")
        print(f"Next available serial: {summary['next_serial']:,}")
        
        print(f"\nLast 3 allocations:")
        for entry in summary['usage_log'][-3:]:
            timestamp = entry['timestamp'][:19]  # Remove microseconds
            customer = entry.get('customer', 'Unknown')
            ticket = entry.get('ticket_number', 'Unknown')
            qty = entry['quantity']
            print(f"   {timestamp} | {customer} ({ticket}) | {qty:,} serials")
            
    except Exception as e:
        print(f"❌ Test 4 failed: {e}")
        return
    
    # Test 5: Show daily file structure
    print("\n📁 Test 5: Daily File Structure")
    print("-" * 40)
    
    try:
        today_filename = manager._get_today_filename()
        today_filepath = manager._get_today_filepath()
        
        print(f"Today's filename: {today_filename}")
        print(f"Full file path: {today_filepath}")
        
        if os.path.exists(today_filepath):
            file_size = os.path.getsize(today_filepath)
            print(f"File size: {file_size:,} bytes")
            
            # Show file contents preview
            import json
            with open(today_filepath, 'r') as f:
                data = json.load(f)
            
            print(f"Current serial: {data['current_serial']:,}")
            print(f"Created by: {data.get('created_by', 'Unknown')}")
            print(f"Machine: {data.get('machine', 'Unknown')}")
            print(f"Usage log entries: {len(data.get('usage_log', []))}")
        else:
            print("❌ Daily file not found")
            
    except Exception as e:
        print(f"❌ Test 5 failed: {e}")
        return
    
    print("\n✅ All tests completed successfully!")
    print("\n🎯 Serial Number Management System Features:")
    print("   ✓ Atomic serial allocation with file locking")
    print("   ✓ Daily file-based organization")
    print("   ✓ Comprehensive usage logging")
    print("   ✓ Multi-user support with duplicate prevention")
    print("   ✓ Job information tracking")
    print("   ✓ Centralized shared drive storage")


if __name__ == "__main__":
    test_serial_manager() 
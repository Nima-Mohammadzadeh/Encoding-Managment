#!/usr/bin/env python3
"""
Test script to demonstrate and verify EPC generation performance improvements.
This script tests both the old blocking method and new threaded method.
"""

import os
import sys
import time
import tempfile
import shutil
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.epc_conversion import (
    generate_epc_database_files,
    generate_epc_database_files_with_progress,
    validate_upc
)

def test_blocking_generation(upc, start_serial, total_qty, qty_per_db, test_dir):
    """Test the original blocking EPC generation."""
    print(f"\n{'='*60}")
    print("TESTING BLOCKING GENERATION (Original Method)")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        created_files = generate_epc_database_files(
            upc, start_serial, total_qty, qty_per_db, test_dir
        )
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ Blocking generation completed successfully!")
        print(f"⏱️  Duration: {duration:.2f} seconds")
        print(f"📁 Files created: {len(created_files)}")
        print(f"🎯 Records per file: {qty_per_db:,}")
        print(f"📊 Total records: {total_qty:,}")
        print(f"⚡ Records per second: {total_qty/duration:,.0f}")
        
        return duration, len(created_files)
        
    except Exception as e:
        print(f"❌ Blocking generation failed: {e}")
        return None, 0

def progress_callback(percentage, message):
    """Progress callback for threaded generation test."""
    print(f"📈 {percentage:3d}%: {message}")

def cancel_check():
    """Cancel check for threaded generation test."""
    return False  # Never cancel in this test

def test_threaded_generation(upc, start_serial, total_qty, qty_per_db, test_dir):
    """Test the new threaded EPC generation with progress."""
    print(f"\n{'='*60}")
    print("TESTING THREADED GENERATION (New Method)")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        created_files = generate_epc_database_files_with_progress(
            upc, start_serial, total_qty, qty_per_db, test_dir,
            progress_callback=progress_callback,
            cancel_check=cancel_check
        )
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ Threaded generation completed successfully!")
        print(f"⏱️  Duration: {duration:.2f} seconds")
        print(f"📁 Files created: {len(created_files)}")
        print(f"🎯 Records per file: {qty_per_db:,}")
        print(f"📊 Total records: {total_qty:,}")
        print(f"⚡ Records per second: {total_qty/duration:,.0f}")
        
        return duration, len(created_files)
        
    except Exception as e:
        print(f"❌ Threaded generation failed: {e}")
        return None, 0

def run_performance_test():
    """Run comprehensive performance tests."""
    print("🚀 EPC Generation Performance Test")
    print("=" * 60)
    
    # Test parameters
    test_upc = "123456789012"
    start_serial = 1
    qty_per_db = 1000
    
    # Test different quantities
    test_quantities = [5000, 10000, 25000]
    
    if not validate_upc(test_upc):
        print(f"❌ Invalid test UPC: {test_upc}")
        return
    
    print(f"🏷️  Test UPC: {test_upc}")
    print(f"🔢 Starting Serial: {start_serial}")
    print(f"📦 Records per DB: {qty_per_db:,}")
    print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    for total_qty in test_quantities:
        print(f"\n{'*'*60}")
        print(f"TESTING WITH {total_qty:,} RECORDS")
        print(f"{'*'*60}")
        
        # Create temporary directories for each test
        blocking_dir = tempfile.mkdtemp(prefix=f"epc_blocking_{total_qty}_")
        threaded_dir = tempfile.mkdtemp(prefix=f"epc_threaded_{total_qty}_")
        
        try:
            # Test blocking generation
            blocking_time, blocking_files = test_blocking_generation(
                test_upc, start_serial, total_qty, qty_per_db, blocking_dir
            )
            
            # Small delay between tests
            time.sleep(1)
            
            # Test threaded generation
            threaded_time, threaded_files = test_threaded_generation(
                test_upc, start_serial, total_qty, qty_per_db, threaded_dir
            )
            
            # Store results
            if blocking_time and threaded_time:
                improvement = ((blocking_time - threaded_time) / blocking_time) * 100
                results.append({
                    'quantity': total_qty,
                    'blocking_time': blocking_time,
                    'threaded_time': threaded_time,
                    'improvement': improvement,
                    'files': blocking_files
                })
                
                print(f"\n📊 COMPARISON FOR {total_qty:,} RECORDS:")
                print(f"   Blocking method:  {blocking_time:.2f}s")
                print(f"   Threaded method:  {threaded_time:.2f}s")
                print(f"   Performance gain: {improvement:+.1f}%")
            
        finally:
            # Clean up temporary directories
            try:
                shutil.rmtree(blocking_dir)
                shutil.rmtree(threaded_dir)
            except Exception as e:
                print(f"⚠️  Cleanup warning: {e}")
    
    # Print summary
    print(f"\n{'='*60}")
    print("PERFORMANCE TEST SUMMARY")
    print(f"{'='*60}")
    
    if results:
        print(f"{'Quantity':<12} {'Blocking':<12} {'Threaded':<12} {'Improvement':<12} {'Files':<8}")
        print("-" * 60)
        
        for result in results:
            print(f"{result['quantity']:,<12} "
                  f"{result['blocking_time']:.2f}s{'':<6} "
                  f"{result['threaded_time']:.2f}s{'':<6} "
                  f"{result['improvement']:+.1f}%{'':<6} "
                  f"{result['files']}")
        
        avg_improvement = sum(r['improvement'] for r in results) / len(results)
        print(f"\n📈 Average performance improvement: {avg_improvement:+.1f}%")
        
        # Check if threaded is consistently faster
        all_faster = all(r['improvement'] > 0 for r in results)
        if all_faster:
            print("✅ Threaded method is consistently faster!")
        else:
            print("⚠️  Mixed results - check implementation")
    else:
        print("❌ No valid test results obtained")
    
    print(f"\n🏁 Performance test completed at {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    try:
        run_performance_test()
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc() 
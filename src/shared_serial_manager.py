"""
Shared Serial Number Manager for Encoding Management
This module handles serial number assignment using a shared file on the Z: drive.
No HTTP server required - much safer for workplace deployment.
"""

import json
import os
import time
import sys
from datetime import datetime
from typing import Dict, Any, Tuple
import random

# Import platform-specific modules for file locking
try:
    import fcntl  # For file locking on Unix-like systems
except ImportError:
    fcntl = None

try:
    import msvcrt  # For file locking on Windows
except ImportError:
    msvcrt = None


class SharedSerialManager:
    def __init__(self, shared_path: str = None):
        """
        Initialize the shared serial number manager.
        
        Args:
            shared_path: Path to the shared directory (defaults to Z: drive)
        """
        if shared_path is None:
            shared_path = r"Z:\3 Encoding and Printing Files\Customers Encoding Files"
        
        self.shared_path = shared_path
        self.serial_file = os.path.join(shared_path, ".encoding_serials.json")
        self.lock_file = os.path.join(shared_path, ".encoding_serials.lock")
        
        # Create the data file if it doesn't exist
        self._initialize_serial_file()
    
    def _initialize_serial_file(self):
        """Initialize the serial number file if it doesn't exist."""
        if not os.path.exists(self.serial_file):
            try:
                initial_data = {
                    "current_serial": 1000,  # Starting serial number
                    "last_updated": datetime.now().isoformat(),
                    "total_issued": 0,
                    "last_updated_by": os.environ.get("USERNAME", "Unknown"),
                    "version": "1.0"
                }
                
                with open(self.serial_file, 'w') as f:
                    json.dump(initial_data, f, indent=2)
                    
                print(f"✅ Initialized serial number file at: {self.serial_file}")
                
            except Exception as e:
                print(f"⚠️  Could not initialize serial file: {e}")
    
    def _acquire_lock(self, max_retries: int = 30, retry_delay: float = 0.5) -> bool:
        """
        Acquire a file lock to ensure only one process accesses serials at a time.
        
        Args:
            max_retries: Maximum number of lock attempts
            retry_delay: Delay between lock attempts in seconds
            
        Returns:
            True if lock acquired, False otherwise
        """
        for attempt in range(max_retries):
            try:
                # Create lock file if it doesn't exist
                if not os.path.exists(self.lock_file):
                    with open(self.lock_file, 'w') as f:
                        f.write(f"Locked by {os.environ.get('USERNAME', 'Unknown')} at {datetime.now()}")
                    return True
                else:
                    # Check if lock file is stale (older than 30 seconds)
                    lock_age = time.time() - os.path.getmtime(self.lock_file)
                    if lock_age > 30:
                        print(f"⚠️  Removing stale lock file (age: {lock_age:.1f}s)")
                        os.remove(self.lock_file)
                        continue
                    
                    # Wait and retry
                    time.sleep(retry_delay + random.uniform(0, 0.1))  # Add jitter
                    
            except (OSError, IOError):
                time.sleep(retry_delay)
        
        return False
    
    def _release_lock(self):
        """Release the file lock."""
        try:
            if os.path.exists(self.lock_file):
                os.remove(self.lock_file)
        except (OSError, IOError) as e:
            print(f"⚠️  Could not remove lock file: {e}")
    
    def get_serial_range(self, quantity: int) -> Dict[str, Any]:
        """
        Get a range of serial numbers for the given quantity.
        
        Args:
            quantity: Number of serial numbers needed
            
        Returns:
            Dict with success, start_serial, end_serial, and other info
        """
        if quantity <= 0:
            return {
                "success": False,
                "error": "Quantity must be greater than 0"
            }
        
        if quantity > 100000:  # Safety limit
            return {
                "success": False,
                "error": "Quantity too large (max 100,000)"
            }
        
        # Check if shared path is accessible
        if not os.path.exists(self.shared_path):
            return {
                "success": False,
                "error": f"Shared path not accessible: {self.shared_path}"
            }
        
        # Try to acquire lock
        if not self._acquire_lock():
            return {
                "success": False,
                "error": "Could not acquire lock - another user may be creating a job. Please try again in a moment."
            }
        
        try:
            # Read current serial data
            if not os.path.exists(self.serial_file):
                self._initialize_serial_file()
            
            with open(self.serial_file, 'r') as f:
                data = json.load(f)
            
            # Calculate serial range
            start_serial = data["current_serial"]
            end_serial = start_serial + quantity - 1
            
            # Update data
            data["current_serial"] = end_serial + 1
            data["last_updated"] = datetime.now().isoformat()
            data["total_issued"] = data.get("total_issued", 0) + quantity
            data["last_updated_by"] = os.environ.get("USERNAME", "Unknown")
            
            # Write updated data
            with open(self.serial_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"✅ Assigned serial range: {start_serial} to {end_serial} (qty: {quantity})")
            
            return {
                "success": True,
                "start_serial": start_serial,
                "end_serial": end_serial,
                "quantity": quantity,
                "next_available": data["current_serial"]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error processing serial assignment: {str(e)}"
            }
        
        finally:
            # Always release the lock
            self._release_lock()
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the serial number system.
        
        Returns:
            Dict with current serial number information
        """
        try:
            if not os.path.exists(self.serial_file):
                return {
                    "success": False,
                    "error": "Serial number file not found"
                }
            
            with open(self.serial_file, 'r') as f:
                data = json.load(f)
            
            return {
                "success": True,
                "current_serial": data["current_serial"],
                "last_updated": data["last_updated"],
                "total_issued": data.get("total_issued", 0),
                "last_updated_by": data.get("last_updated_by", "Unknown"),
                "shared_path": self.shared_path
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error reading serial status: {str(e)}"
            }


# Global instance
_shared_serial_manager = None


def initialize_shared_serial_manager(shared_path: str = None) -> bool:
    """
    Initialize the global shared serial manager.
    
    Args:
        shared_path: Path to shared directory (defaults to Z: drive)
        
    Returns:
        True if initialization successful, False otherwise
    """
    global _shared_serial_manager
    
    try:
        _shared_serial_manager = SharedSerialManager(shared_path)
        status = _shared_serial_manager.get_status()
        return status.get("success", False)
    except Exception as e:
        print(f"❌ Error initializing shared serial manager: {e}")
        return False


def get_serial_range(quantity: int) -> Dict[str, Any]:
    """
    Get a range of serial numbers using the global manager.
    
    Args:
        quantity: Number of serial numbers needed
        
    Returns:
        Dict with serial range or error information
    """
    if _shared_serial_manager is None:
        return {
            "success": False,
            "error": "Shared serial manager not initialized"
        }
    
    return _shared_serial_manager.get_serial_range(quantity)


def get_status() -> Dict[str, Any]:
    """
    Get the status of the shared serial system.
    
    Returns:
        Dict with status information
    """
    if _shared_serial_manager is None:
        return {
            "success": False,
            "error": "Shared serial manager not initialized"
        }
    
    return _shared_serial_manager.get_status() 
"""
Centralized Serial Number Management System

This module provides thread-safe, multi-user serial number allocation
for EPC generation to ensure globally unique serial numbers across
all users and workstations.

Features:
- Daily serial number files on shared drive
- Atomic serial number allocation with file locking
- Usage logging with timestamps and job information
- Automatic file creation and directory setup
- Integration with all EPC generation workflows
"""

import os
import json
import threading
import time
from datetime import datetime, date
from pathlib import Path
import platform
from typing import Dict, Optional, Tuple

# Import file locking modules based on platform
try:
    if platform.system() == "Windows":
        import msvcrt
    else:
        import fcntl
except ImportError:
    print("Warning: File locking not available on this platform")


class SerialNumberManager:
    """
    Thread-safe serial number manager for multi-user EPC generation.
    
    Manages daily serial number files on shared drive with usage logging
    and atomic allocation to prevent duplicates across all users.
    """
    
    def __init__(self, base_path: str = None):
        """
        Initialize serial number manager.
        
        Args:
            base_path (str): Base path for serial number files.
                           Defaults to Z:\3 Encoding and Printing Files\Serial Numbers
        """
        self.base_path = base_path or r"Z:\3 Encoding and Printing Files\Serial Numbers"
        self.lock = threading.Lock()
        self._ensure_base_directory()
    
    def _ensure_base_directory(self):
        """Ensure the base serial numbers directory exists."""
        try:
            os.makedirs(self.base_path, exist_ok=True)
        except Exception as e:
            print(f"Warning: Could not create serial numbers directory: {e}")
    
    def _get_today_filename(self) -> str:
        """Get the filename for today's serial number file."""
        today = date.today().strftime("%Y-%m-%d")
        return f"serials_{today}.json"
    
    def _get_today_filepath(self) -> str:
        """Get the full file path for today's serial number file."""
        return os.path.join(self.base_path, self._get_today_filename())
    
    def _lock_file(self, file_handle):
        """Lock file for exclusive access (cross-platform)."""
        try:
            if platform.system() == "Windows":
                # Windows file locking
                while True:
                    try:
                        msvcrt.locking(file_handle.fileno(), msvcrt.LK_NBLCK, 1)
                        break
                    except IOError:
                        time.sleep(0.01)  # Wait 10ms and retry
            else:
                # Unix-like file locking
                fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX)
        except (NameError, AttributeError):
            # File locking not available, continue without it
            pass
    
    def _unlock_file(self, file_handle):
        """Unlock file (cross-platform)."""
        try:
            if platform.system() == "Windows":
                msvcrt.locking(file_handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)
        except (NameError, AttributeError):
            # File locking not available, continue without it
            pass
    
    def _load_daily_data(self, filepath: str) -> Dict:
        """
        Load or create daily serial number data.
        
        Returns:
            dict: Daily data structure with current_serial and usage_log
        """
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    # Ensure required keys exist
                    if 'current_serial' not in data:
                        data['current_serial'] = 1000  # Default starting serial
                    if 'usage_log' not in data:
                        data['usage_log'] = []
                    return data
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load serial data, creating new: {e}")
        
        # Create new daily data structure
        return {
            'current_serial': 1000,  # Starting serial number
            'usage_log': [],
            'created_date': date.today().isoformat(),
            'created_by': os.getenv('USERNAME', 'unknown'),
            'machine': os.getenv('COMPUTERNAME', 'unknown')
        }
    
    def _save_daily_data(self, filepath: str, data: Dict):
        """Save daily serial number data to file."""
        try:
            # Write to temporary file first, then rename for atomic operation
            temp_path = filepath + '.tmp'
            with open(temp_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Atomic rename
            if os.path.exists(filepath):
                os.replace(temp_path, filepath)
            else:
                os.rename(temp_path, filepath)
                
        except Exception as e:
            print(f"Error saving serial data: {e}")
            # Clean up temp file if it exists
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            raise
    
    def allocate_serials(self, quantity: int, job_info: Dict = None) -> Tuple[int, int]:
        """
        Allocate a range of serial numbers atomically.
        
        Args:
            quantity (int): Number of serial numbers to allocate
            job_info (dict): Job information for logging (optional)
        
        Returns:
            tuple: (start_serial, end_serial) - inclusive range
        
        Raises:
            Exception: If allocation fails
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        filepath = self._get_today_filepath()
        
        with self.lock:  # Thread-level lock
            try:
                # Load current data
                data = self._load_daily_data(filepath)
                
                # Allocate serial range
                start_serial = data['current_serial']
                end_serial = start_serial + quantity - 1
                data['current_serial'] = end_serial + 1
                
                # Log the allocation
                log_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'start_serial': start_serial,
                    'end_serial': end_serial,
                    'quantity': quantity,
                    'user': os.getenv('USERNAME', 'unknown'),
                    'machine': os.getenv('COMPUTERNAME', 'unknown')
                }
                
                # Add job information if provided
                if job_info:
                    log_entry.update({
                        'customer': job_info.get('customer', ''),
                        'po_number': job_info.get('po_number', ''),
                        'ticket_number': job_info.get('ticket_number', ''),
                        'upc': job_info.get('upc', ''),
                        'label_size': job_info.get('label_size', '')
                    })
                
                data['usage_log'].append(log_entry)
                
                # Save updated data
                self._save_daily_data(filepath, data)
                
                return start_serial, end_serial
                
            except Exception as e:
                print(f"Error in serial allocation: {e}")
                raise
    
    def get_next_serial(self) -> int:
        """
        Get the next available serial number without allocating it.
        
        Returns:
            int: Next available serial number
        """
        filepath = self._get_today_filepath()
        data = self._load_daily_data(filepath)
        return data['current_serial']
    
    def get_daily_usage_summary(self, target_date: date = None) -> Dict:
        """
        Get usage summary for a specific date.
        
        Args:
            target_date (date): Date to get summary for (defaults to today)
        
        Returns:
            dict: Usage summary with total allocated, log entries, etc.
        """
        if target_date is None:
            target_date = date.today()
        
        filename = f"serials_{target_date.strftime('%Y-%m-%d')}.json"
        filepath = os.path.join(self.base_path, filename)
        
        if not os.path.exists(filepath):
            return {
                'date': target_date.isoformat(),
                'total_allocated': 0,
                'allocations_count': 0,
                'usage_log': [],
                'next_serial': 1000
            }
        
        data = self._load_daily_data(filepath)
        
        total_allocated = 0
        for entry in data.get('usage_log', []):
            total_allocated += entry.get('quantity', 0)
        
        return {
            'date': target_date.isoformat(),
            'total_allocated': total_allocated,
            'allocations_count': len(data.get('usage_log', [])),
            'usage_log': data.get('usage_log', []),
            'next_serial': data.get('current_serial', 1000)
        }
    
    def validate_base_path(self) -> Tuple[bool, str]:
        """
        Validate that the base path is accessible.
        
        Returns:
            tuple: (is_valid, message)
        """
        try:
            # Check if it's a network path
            is_network_path = self.base_path.startswith('\\\\') or (len(self.base_path) > 1 and self.base_path[1] == ':' and self.base_path[0].upper() >= 'Z')
            
            if not os.path.exists(self.base_path):
                if is_network_path:
                    return False, f"Network drive not accessible or not mapped: {self.base_path}"
                else:
                    # Try to create local directory
                    os.makedirs(self.base_path, exist_ok=True)
            
            # Test write access
            test_file = os.path.join(self.base_path, 'test_access.tmp')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            
            return True, f"Serial numbers path is accessible: {self.base_path}"
            
        except PermissionError as e:
            return False, f"Permission denied accessing serial numbers path: {self.base_path}. Check network drive permissions or mapping."
        except FileNotFoundError as e:
            return False, f"Serial numbers path not found: {self.base_path}. Check if network drive is mapped."
        except Exception as e:
            return False, f"Cannot access serial numbers path: {self.base_path}. Error: {e}"


# Global instance for application-wide use
_serial_manager = None

def get_serial_manager(base_path: str = None) -> SerialNumberManager:
    """
    Get the global serial number manager instance.
    
    Args:
        base_path (str): Base path for serial files (used only on first call)
    
    Returns:
        SerialNumberManager: Global serial manager instance
    """
    global _serial_manager
    if _serial_manager is None or (base_path and base_path != _serial_manager.base_path):
        _serial_manager = SerialNumberManager(base_path)
    return _serial_manager


def allocate_serials_for_job(quantity: int, job_data: Dict = None) -> Tuple[int, int]:
    """
    Convenience function to allocate serials for a job.
    
    Args:
        quantity (int): Number of serials to allocate
        job_data (dict): Job information for logging
    
    Returns:
        tuple: (start_serial, end_serial)
    """
    manager = get_serial_manager()
    
    # Extract relevant job info for logging
    job_info = {}
    if job_data:
        job_info = {
            'customer': job_data.get('Customer', ''),
            'po_number': job_data.get('PO#', ''),
            'ticket_number': job_data.get('Ticket#', job_data.get('Job Ticket#', '')),
            'upc': job_data.get('UPC Number', ''),
            'label_size': job_data.get('Label Size', '')
        }
    
    return manager.allocate_serials(quantity, job_info)


def get_next_available_serial() -> int:
    """
    Get the next available serial number.
    
    Returns:
        int: Next available serial number
    """
    manager = get_serial_manager()
    return manager.get_next_serial()


def reset_serial_manager():
    """Reset the global serial manager instance to pick up new configuration."""
    global _serial_manager
    _serial_manager = None 
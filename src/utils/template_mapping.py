"""
Template Mapping Manager
Manages the mapping of Customer + Label Size pairs to specific template files.
"""

import json
import os
from typing import Dict, Optional
import src.config as config


class TemplateMappingManager:
    """Manages template mappings stored in a JSON file."""
    
    def __init__(self):
        self._mappings: Dict[str, Dict[str, str]] = {}
        self._mapping_file_path: Optional[str] = None
        self.load_mappings()
    
    def load_mappings(self) -> bool:
        """Load mappings from the configured JSON file."""
        mapping_file = config.get_template_mapping_file()
        
        if not mapping_file or not os.path.exists(mapping_file):
            print(f"Template mapping file not found or not configured: {mapping_file}")
            self._mappings = {}
            return False
        
        try:
            with open(mapping_file, 'r', encoding='utf-8') as f:
                self._mappings = json.load(f)
            self._mapping_file_path = mapping_file
            print(f"Loaded {len(self._mappings)} customer template mappings from {mapping_file}")
            return True
        except json.JSONDecodeError as e:
            print(f"Error parsing template mapping file: {e}")
            self._mappings = {}
            return False
        except Exception as e:
            print(f"Error loading template mapping file: {e}")
            self._mappings = {}
            return False
    
    def save_mappings(self) -> bool:
        """Save current mappings to the JSON file."""
        mapping_file = self._mapping_file_path or config.get_template_mapping_file()
        
        if not mapping_file:
            print("No template mapping file configured")
            return False
        
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(mapping_file), exist_ok=True)
            
            # Save with pretty formatting
            with open(mapping_file, 'w', encoding='utf-8') as f:
                json.dump(self._mappings, f, indent=2, sort_keys=True)
            
            print(f"Saved template mappings to {mapping_file}")
            return True
        except Exception as e:
            print(f"Error saving template mapping file: {e}")
            return False
    
    def get_template(self, customer: str, label_size: str) -> Optional[str]:
        """
        Get the template path for a given customer and label size.
        Returns None if no mapping exists or the mapped file doesn't exist.
        """
        if not customer or not label_size:
            return None
        
        # Check if customer exists in mappings
        if customer not in self._mappings:
            return None
        
        # Check if label size exists for this customer
        customer_mappings = self._mappings[customer]
        if label_size not in customer_mappings:
            return None
        
        template_path = customer_mappings[label_size]
        
        # Verify the template file exists
        if os.path.exists(template_path):
            return template_path
        else:
            print(f"Mapped template file not found: {template_path}")
            return None
    
    def set_template(self, customer: str, label_size: str, template_path: str) -> bool:
        """
        Set the template path for a given customer and label size.
        Returns True if successful.
        """
        if not customer or not label_size or not template_path:
            return False
        
        # Initialize customer entry if it doesn't exist
        if customer not in self._mappings:
            self._mappings[customer] = {}
        
        # Set the mapping
        self._mappings[customer][label_size] = template_path
        return True
    
    def remove_template(self, customer: str, label_size: str) -> bool:
        """
        Remove the template mapping for a given customer and label size.
        Returns True if successful.
        """
        if customer not in self._mappings:
            return False
        
        if label_size not in self._mappings[customer]:
            return False
        
        del self._mappings[customer][label_size]
        
        # Remove customer entry if empty
        if not self._mappings[customer]:
            del self._mappings[customer]
        
        return True
    
    def get_all_mappings(self) -> Dict[str, Dict[str, str]]:
        """Get a copy of all mappings."""
        return self._mappings.copy()
    
    def get_customer_mappings(self, customer: str) -> Dict[str, str]:
        """Get all mappings for a specific customer."""
        return self._mappings.get(customer, {}).copy()
    
    def get_all_customers(self) -> list:
        """Get a list of all customers with mappings."""
        return sorted(self._mappings.keys())
    
    def clear_mappings(self):
        """Clear all mappings."""
        self._mappings = {}
    
    def reload_mappings(self) -> bool:
        """Reload mappings from file."""
        return self.load_mappings()


# Global instance
_template_manager = None


def get_template_manager() -> TemplateMappingManager:
    """Get the global template mapping manager instance."""
    global _template_manager
    if _template_manager is None:
        _template_manager = TemplateMappingManager()
    return _template_manager 
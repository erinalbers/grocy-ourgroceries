"""
Item matcher for Grocy-OurGroceries sync.
Handles matching items between Grocy and OurGroceries.
"""

import logging
import re
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class ItemMatcher:
    def __init__(self, name_mappings: Dict[str, str], quantity_separator: str):
        """
        Initialize the item matcher.
        
        Args:
            name_mappings: Dictionary mapping Grocy product names to OurGroceries item names
            quantity_separator: Separator used between item name and quantity
        """
        self.name_mappings = name_mappings
        self.quantity_separator = quantity_separator
    
    def map_item_name(self, grocy_name: str) -> str:
        """
        Map a Grocy product name to an OurGroceries item name.
        
        Args:
            grocy_name: The name of the product in Grocy
            
        Returns:
            The mapped name for OurGroceries
        """
        if grocy_name in self.name_mappings:
            return self.name_mappings[grocy_name]
        return grocy_name
    
    def extract_base_name(self, item_value: str) -> str:
        """
        Extract the base product name without quantity information.
        
        Args:
            item_value: The full item name possibly including quantity
            
        Returns:
            The base product name without quantity information
        """
        # Convert to lowercase for case-insensitive comparison
        item_lower = item_value.lower()
        
        # Check if the item follows our configured format "name {separator} quantity"
        if self.quantity_separator in item_lower:
            return item_lower.split(self.quantity_separator)[0].strip()
        
        # For backward compatibility, handle the old format with parentheses
        if '(' in item_lower:
            # Extract just the name part before the parentheses
            base_item_value = item_lower
            if '(' in base_item_value:
                base_item_value = base_item_value.split('(')[0].strip()
            
            return base_item_value
        
        # If no quantity pattern is found, return the original string
        return item_lower
    
    def find_matching_item(self, grocy_name: str, og_items: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Find a matching item in OurGroceries list for a Grocy product.
        
        Args:
            grocy_name: The name of the product in Grocy
            og_items: List of items from OurGroceries
            
        Returns:
            The matching item or None if not found
        """
        og_item_name = self.map_item_name(grocy_name)
        og_item_name_lower = og_item_name.lower()
        
        for og_item in og_items:
            if isinstance(og_item, dict) and 'value' in og_item and 'id' in og_item:
                base_item_value = self.extract_base_name(og_item['value'])
                
                logger.debug(f"Comparing: Grocy item '{og_item_name_lower}' with OG item base '{base_item_value}'")
                
                # Check if the item names match
                if og_item_name_lower == base_item_value:
                    logger.debug(f"Found existing item '{og_item_name}' in OurGroceries list as '{og_item['value']}'")
                    return og_item
        
        return None
        
    def extract_existing_quantity(self, item: Dict[str, Any]) -> Optional[str]:
        """
        Extract quantity information from an existing OurGroceries item.
        
        Args:
            item: The OurGroceries item
            
        Returns:
            The quantity string or None if not found
        """
        if not isinstance(item, dict) or 'value' not in item:
            return None
            
        # Check if the item follows our configured format "name {separator} quantity"
        if self.quantity_separator in item['value']:
            parts = item['value'].split(self.quantity_separator, 1)
            if len(parts) > 1:
                return parts[1]
        else:
            # For backward compatibility, handle the old format with parentheses
            import re
            # Match the quantity in parentheses, ignoring any counter in additional parentheses
            match = re.search(r'\(([^()]+)\)(?:\s*\(\d+\))?', item['value'])
            if match:
                return match.group(1)
                
        return None
        
    def has_quantity_changed(self, existing_quantity: Optional[str], new_quantity: str) -> bool:
        """
        Check if the quantity has changed between existing and new values.
        
        Args:
            existing_quantity: The existing quantity string
            new_quantity: The new quantity string
            
        Returns:
            True if the quantity has changed, False otherwise
        """
        if existing_quantity != new_quantity:
            # Try to normalize quantities for comparison (remove spaces, lowercase)
            normalized_existing = existing_quantity.lower().replace(' ', '') if existing_quantity else ''
            normalized_new = new_quantity.lower().replace(' ', '') if new_quantity else ''
            
            return normalized_existing != normalized_new
            
        return False

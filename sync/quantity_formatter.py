"""
Quantity formatter for Grocy-OurGroceries sync.
Handles formatting and converting quantities between different units.
"""

import logging
import json
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

class QuantityFormatter:
    def __init__(self, grocy_client, quantity_separator: str):
        """
        Initialize the quantity formatter.
        
        Args:
            grocy_client: Initialized Grocy API client
            quantity_separator: Separator used between item name and quantity
        """
        self.grocy_client = grocy_client
        self.quantity_separator = quantity_separator
    
    def format_quantity(self, grocy_item: Dict[str, Any]) -> Tuple[Any, Optional[str]]:
        """
        Format quantity information from a Grocy item.
        
        Args:
            grocy_item: The item from Grocy
            
        Returns:
            A tuple of (quantity_value, quantity_string)
        """
        # Get the original quantity from the shopping list item
        original_quantity = grocy_item.get('amount', '')
        logger.debug(f"Original quantity from Grocy: {original_quantity}, type: {type(original_quantity)}")
        
        # Initialize variables for unit conversion
        quantity = original_quantity
        unit = None
        
        # Check if we need to convert between units
        if 'product_details' in grocy_item and grocy_item['product_details']:
            product = grocy_item['product_details']
            
            # Get the shopping list item's quantity unit ID
            shopping_list_qu_id = grocy_item.get('qu_id')
            
            # Get the product's purchase and stock quantity unit IDs
            product_purchase_qu_id = product.get('qu_id_purchase')
            product_stock_qu_id = product.get('qu_id_stock')
            
            logger.debug(f"Shopping list qu_id: {shopping_list_qu_id}, Purchase qu_id: {product_purchase_qu_id}, Stock qu_id: {product_stock_qu_id}")
            
            # CASE 1: If shopping list unit matches purchase unit but differs from stock unit,
            # we need to convert from stock to purchase units
            if (shopping_list_qu_id == product_purchase_qu_id and 
                product_purchase_qu_id != product_stock_qu_id):
                
                # Find the conversion factor from stock to purchase
                conversion_factor = self._find_conversion_factor(product, product_stock_qu_id, product_purchase_qu_id)
                
                # Apply conversion if factor found
                if conversion_factor:
                    try:
                        stock_quantity = float(original_quantity)
                        purchase_quantity = stock_quantity * conversion_factor
                        
                        # Round to 2 decimal places, but convert to int if it's close to a whole number
                        purchase_quantity = round(purchase_quantity, 2)
                        if abs(purchase_quantity - round(purchase_quantity)) < 0.05:
                            purchase_quantity = round(purchase_quantity)
                        
                        logger.debug(f"Converted quantity from {original_quantity} (stock) to {purchase_quantity} (purchase)")
                        quantity = purchase_quantity
                    except (ValueError, TypeError) as e:
                        logger.error(f"Error converting quantity: {e}")
            
            # CASE 2: If shopping list unit differs from purchase unit,
            # we need to convert from shopping list unit to purchase unit
            elif shopping_list_qu_id != product_purchase_qu_id:
                logger.debug(f"Shopping list unit ({shopping_list_qu_id}) differs from purchase unit ({product_purchase_qu_id})")
                
                # Find the conversion factor from shopping list to purchase
                conversion_factor = self._find_conversion_factor(product, shopping_list_qu_id, product_purchase_qu_id)
                
                # Apply conversion if factor found
                if conversion_factor:
                    try:
                        shopping_list_quantity = float(original_quantity)
                        purchase_quantity = shopping_list_quantity * conversion_factor
                        
                        # Round to 2 decimal places, but convert to int if it's close to a whole number
                        purchase_quantity = round(purchase_quantity, 2)
                        if abs(purchase_quantity - round(purchase_quantity)) < 0.05:
                            purchase_quantity = round(purchase_quantity)
                        
                        logger.debug(f"Converted quantity from {original_quantity} ({shopping_list_qu_id}) to {purchase_quantity} ({product_purchase_qu_id})")
                        quantity = purchase_quantity
                        
                        # Use purchase unit instead of shopping list unit
                        shopping_list_qu_id = product_purchase_qu_id
                    except (ValueError, TypeError) as e:
                        logger.error(f"Error converting quantity: {e}")
            
            # Get the appropriate unit (shopping list unit or converted unit)
            if shopping_list_qu_id:
                # Use shopping list quantity unit
                qu_id = shopping_list_qu_id
                quantity_unit = self.grocy_client.get_quantity_unit(qu_id)
                logger.debug(f"Using shopping list quantity unit (ID: {qu_id}) for {product.get('name')}")
            else:
                quantity_unit = None
                logger.debug(f"No quantity unit found for {product.get('name')}")
        else:
            # If no product details, use regular quantity unit from shopping list
            qu_id = grocy_item.get('qu_id')
            if qu_id:
                quantity_unit = self.grocy_client.get_quantity_unit(qu_id)
                logger.debug(f"Using regular quantity unit (ID: {qu_id}) - no product details available")
            else:
                quantity_unit = None
        
        # Process the quantity unit if we found one
        if quantity_unit:
            unit = self._get_unit_name(quantity_unit, quantity)
        
        quantity_str = str(quantity)
        if unit:
            quantity_str = f"{quantity} {unit}"
        
        return quantity, quantity_str

    def _find_conversion_factor(self, product: Dict[str, Any], from_qu_id: int, to_qu_id: int) -> Optional[float]:
        """
        Find a conversion factor between two quantity units.
        
        Args:
            product: The product details
            from_qu_id: Source quantity unit ID
            to_qu_id: Target quantity unit ID
            
        Returns:
            Conversion factor or None if not found
        """
        if 'quantity_unit_conversions' not in product:
            return None
            
        # Try to find direct conversion
        for conversion in product['quantity_unit_conversions']:
            if (conversion.get('from_qu_id') == from_qu_id and 
                conversion.get('to_qu_id') == to_qu_id):
                factor = float(conversion.get('factor', 1))
                logger.debug(f"Found direct conversion factor from {from_qu_id} to {to_qu_id}: {factor}")
                return factor
        
        # If direct conversion not found, try inverse
        for conversion in product['quantity_unit_conversions']:
            if (conversion.get('from_qu_id') == to_qu_id and 
                conversion.get('to_qu_id') == from_qu_id):
                factor = 1 / float(conversion.get('factor', 1))
                logger.debug(f"Found inverse conversion factor from {from_qu_id} to {to_qu_id}: {factor}")
                return factor
        
        logger.debug(f"No conversion factor found from {from_qu_id} to {to_qu_id}")
        return None

    
    def _convert_quantity(self, product: Dict[str, Any], original_quantity: Any, 
                         from_qu_id: str, to_qu_id: str) -> Any:
        """
        Convert quantity between different units.
        
        Args:
            product: The product details from Grocy
            original_quantity: The original quantity value
            from_qu_id: The source quantity unit ID
            to_qu_id: The target quantity unit ID
            
        Returns:
            The converted quantity value
        """
        # Get the conversion factor from the product's quantity unit conversions
        conversion_factor = None
        
        if 'quantity_unit_conversions' in product:
            # First, try to find direct conversion from stock to shopping list unit
            for conversion in product['quantity_unit_conversions']:
                if (conversion.get('from_qu_id') == from_qu_id and 
                    conversion.get('to_qu_id') == to_qu_id):
                    conversion_factor = float(conversion.get('factor', 1))
                    logger.debug(f"Found direct conversion factor: {conversion_factor}")
                    break
            
            # If not found, try to find inverse conversion
            if conversion_factor is None:
                for conversion in product['quantity_unit_conversions']:
                    if (conversion.get('from_qu_id') == to_qu_id and 
                        conversion.get('to_qu_id') == from_qu_id):
                        # This is the inverse conversion
                        conversion_factor = 1 / float(conversion.get('factor', 1))
                        logger.debug(f"Found inverse conversion factor: {conversion_factor}")
                        break
        
        # If we have a conversion factor, convert the quantity
        if conversion_factor and conversion_factor > 0:
            try:
                stock_quantity = float(original_quantity)
                converted_quantity = stock_quantity * conversion_factor
                # Round to 2 decimal places, but convert to int if it's a whole number
                converted_quantity = round(converted_quantity, 2)
                if converted_quantity == int(converted_quantity):
                    converted_quantity = int(converted_quantity)
                
                logger.debug(f"Converted quantity from {original_quantity} to {converted_quantity}")
                return converted_quantity
            except (ValueError, TypeError, ZeroDivisionError) as e:
                logger.error(f"Error converting quantity: {e}")
        
        # Keep the original quantity if conversion fails
        return original_quantity
    
    def _get_unit_name(self, quantity_unit: Dict[str, Any], quantity) -> str:
        """
        Get the appropriate unit name (singular or plural).
        
        Args:
            quantity_unit: The quantity unit details from Grocy
            quantity: The quantity value
            
        Returns:
            The appropriate unit name
        """
        try:
            qty_float = float(quantity)
            if qty_float == 1:
                unit = quantity_unit.get('name', f"unit {quantity_unit.get('id', '')}")
            else:
                # Use plural name if available, otherwise add 's' to singular name
                unit = quantity_unit.get('name_plural', quantity_unit.get('name', f"unit {quantity_unit.get('id', '')}"))
                if unit == quantity_unit.get('name') and not quantity_unit.get('name_plural'):
                    # If plural not available and name doesn't already end with 's'
                    if not unit.endswith('s'):
                        unit = f"{unit}s"
            return unit
        except (ValueError, TypeError):
            # If quantity is not a number, use singular form
            return quantity_unit.get('name', f"unit {quantity_unit.get('id', '')}")

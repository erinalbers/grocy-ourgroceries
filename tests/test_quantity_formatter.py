"""
Tests for the QuantityFormatter class.
"""

import pytest
from unittest.mock import MagicMock, patch

from sync.quantity_formatter import QuantityFormatter

class TestQuantityFormatter:
    """Test suite for the QuantityFormatter class."""
    
    def test_init(self):
        """Test initialization."""
        grocy_client = MagicMock()
        quantity_separator = " : "
        
        formatter = QuantityFormatter(grocy_client, quantity_separator)
        
        assert formatter.grocy_client == grocy_client
        assert formatter.quantity_separator == quantity_separator
    
    def test_format_quantity_simple(self):
        """Test formatting a simple quantity."""
        grocy_client = MagicMock()
        formatter = QuantityFormatter(grocy_client, " : ")
        
        grocy_item = {
            "amount": 3,
            "qu_id": "8"
        }
        
        # Mock the get_quantity_unit method
        grocy_client.get_quantity_unit.return_value = {
            "id": "8",
            "name": "Bottle",
            "name_plural": "Bottles"
        }
        
        quantity, quantity_str = formatter.format_quantity(grocy_item)
        
        assert quantity == 3
        assert quantity_str == "3 Bottles"
        grocy_client.get_quantity_unit.assert_called_once_with("8")
    
    def test_format_quantity_singular(self):
        """Test formatting a singular quantity."""
        grocy_client = MagicMock()
        formatter = QuantityFormatter(grocy_client, " : ")
        
        grocy_item = {
            "amount": 1,
            "qu_id": "8"
        }
        
        # Mock the get_quantity_unit method
        grocy_client.get_quantity_unit.return_value = {
            "id": "8",
            "name": "Bottle",
            "name_plural": "Bottles"
        }
        
        quantity, quantity_str = formatter.format_quantity(grocy_item)
        
        assert quantity == 1
        assert quantity_str == "1 Bottle"
        grocy_client.get_quantity_unit.assert_called_once_with("8")
    
    def test_format_quantity_no_unit(self):
        """Test formatting a quantity with no unit."""
        grocy_client = MagicMock()
        formatter = QuantityFormatter(grocy_client, " : ")
        
        grocy_item = {
            "amount": 3
        }
        
        quantity, quantity_str = formatter.format_quantity(grocy_item)
        
        assert quantity == 3
        assert quantity_str == "3"
        grocy_client.get_quantity_unit.assert_not_called()
    
    def test_format_quantity_with_product_details(self):
        """Test formatting a quantity with product details."""
        grocy_client = MagicMock()
        formatter = QuantityFormatter(grocy_client, " : ")
        
        grocy_item = {
            "amount": 3,
            "qu_id": "8",
            "product_details": {
                "name": "Water",
                "qu_id_stock": "8",
                "qu_id_purchase": "8"
            }
        }
        
        # Mock the get_quantity_unit method
        grocy_client.get_quantity_unit.return_value = {
            "id": "8",
            "name": "Bottle",
            "name_plural": "Bottles"
        }
        
        quantity, quantity_str = formatter.format_quantity(grocy_item)
        
        assert quantity == 3
        assert quantity_str == "3 Bottles"
        grocy_client.get_quantity_unit.assert_called_once_with("8")
    
    def test_format_quantity_with_conversion(self):
        """Test formatting a quantity with unit conversion."""
        grocy_client = MagicMock()
        formatter = QuantityFormatter(grocy_client, " : ")
        
        grocy_item = {
            "amount": 3,
            "qu_id": "8",  # Shopping list unit
            "product_details": {
                "name": "Water",
                "qu_id_stock": "5",  # Stock unit (different from shopping list unit)
                "qu_id_purchase": "8",
                "quantity_unit_conversions": [
                    {
                        "from_qu_id": "5",
                        "to_qu_id": "8",
                        "factor": "2"  # 1 stock unit = 2 shopping list units
                    }
                ]
            }
        }
        
        # Mock the get_quantity_unit method
        grocy_client.get_quantity_unit.return_value = {
            "id": "8",
            "name": "Bottle",
            "name_plural": "Bottles"
        }
        
        quantity, quantity_str = formatter.format_quantity(grocy_item)
        
        assert quantity == 3
        assert quantity_str == "3 Bottles"
        grocy_client.get_quantity_unit.assert_called_once_with("8")
    
    def test_convert_quantity_direct(self):
        """Test converting quantity with direct conversion."""
        grocy_client = MagicMock()
        formatter = QuantityFormatter(grocy_client, " : ")
        
        product = {
            "quantity_unit_conversions": [
                {
                    "from_qu_id": "5",
                    "to_qu_id": "8",
                    "factor": "2"  # 1 stock unit = 2 shopping list units
                }
            ]
        }
        
        result = formatter._convert_quantity(product, 3, "5", "8")
        
        assert result == 6  # 3 stock units * 2 = 6 shopping list units
    
    def test_convert_quantity_inverse(self):
        """Test converting quantity with inverse conversion."""
        grocy_client = MagicMock()
        formatter = QuantityFormatter(grocy_client, " : ")
        
        product = {
            "quantity_unit_conversions": [
                {
                    "from_qu_id": "8",
                    "to_qu_id": "5",
                    "factor": "0.5"  # 1 shopping list unit = 0.5 stock units
                }
            ]
        }
        
        result = formatter._convert_quantity(product, 3, "5", "8")
        
        assert result == 6  # 3 stock units / 0.5 = 6 shopping list units
    
    def test_convert_quantity_no_conversion(self):
        """Test converting quantity with no conversion available."""
        grocy_client = MagicMock()
        formatter = QuantityFormatter(grocy_client, " : ")
        
        product = {
            "quantity_unit_conversions": []
        }
        
        result = formatter._convert_quantity(product, 3, "5", "8")
        
        assert result == 3  # No conversion, return original quantity
    
    def test_get_unit_name_singular(self):
        """Test getting singular unit name."""
        grocy_client = MagicMock()
        formatter = QuantityFormatter(grocy_client, " : ")
        
        quantity_unit = {
            "id": "8",
            "name": "Bottle",
            "name_plural": "Bottles"
        }
        
        result = formatter._get_unit_name(quantity_unit, 1)
        
        assert result == "Bottle"
    
    def test_get_unit_name_plural(self):
        """Test getting plural unit name."""
        grocy_client = MagicMock()
        formatter = QuantityFormatter(grocy_client, " : ")
        
        quantity_unit = {
            "id": "8",
            "name": "Bottle",
            "name_plural": "Bottles"
        }
        
        result = formatter._get_unit_name(quantity_unit, 2)
        
        assert result == "Bottles"
    
    def test_get_unit_name_plural_auto(self):
        """Test getting auto-generated plural unit name."""
        grocy_client = MagicMock()
        formatter = QuantityFormatter(grocy_client, " : ")
        
        quantity_unit = {
            "id": "8",
            "name": "Bottle"
            # No name_plural
        }
        
        result = formatter._get_unit_name(quantity_unit, 2)
        
        assert result == "Bottles"  # Auto-generated plural
    
    def test_get_unit_name_non_numeric(self):
        """Test getting unit name with non-numeric quantity."""
        grocy_client = MagicMock()
        formatter = QuantityFormatter(grocy_client, " : ")
        
        quantity_unit = {
            "id": "8",
            "name": "Bottle",
            "name_plural": "Bottles"
        }
        
        result = formatter._get_unit_name(quantity_unit, "some")
        
        assert result == "Bottle"  # Default to singular for non-numeric

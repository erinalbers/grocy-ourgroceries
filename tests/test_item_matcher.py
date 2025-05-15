"""
Tests for the ItemMatcher class.
"""

import pytest
from unittest.mock import MagicMock

from sync.item_matcher import ItemMatcher

class TestItemMatcher:
    """Test suite for the ItemMatcher class."""
    
    def test_init(self):
        """Test initialization."""
        name_mappings = {"Milk 2%": "Milk (2%)"}
        quantity_separator = " : "
        
        matcher = ItemMatcher(name_mappings, quantity_separator)
        
        assert matcher.name_mappings == name_mappings
        assert matcher.quantity_separator == quantity_separator
    
    def test_map_item_name_with_mapping(self):
        """Test mapping an item name with an existing mapping."""
        name_mappings = {"Milk 2%": "Milk (2%)"}
        matcher = ItemMatcher(name_mappings, " : ")
        
        result = matcher.map_item_name("Milk 2%")
        
        assert result == "Milk (2%)"
    
    def test_map_item_name_without_mapping(self):
        """Test mapping an item name without an existing mapping."""
        name_mappings = {"Milk 2%": "Milk (2%)"}
        matcher = ItemMatcher(name_mappings, " : ")
        
        result = matcher.map_item_name("Eggs")
        
        assert result == "Eggs"
    
    def test_extract_base_name_with_separator(self):
        """Test extracting base name with quantity separator."""
        matcher = ItemMatcher({}, " : ")
        
        result = matcher.extract_base_name("Milk : 1 gallon")
        
        assert result == "milk"
    
    def test_extract_base_name_with_parentheses(self):
        """Test extracting base name with parentheses."""
        matcher = ItemMatcher({}, " : ")
        
        result = matcher.extract_base_name("Milk (1 gallon)")
        
        assert result == "milk"
    
    def test_extract_base_name_no_quantity(self):
        """Test extracting base name with no quantity."""
        matcher = ItemMatcher({}, " : ")
        
        result = matcher.extract_base_name("Milk")
        
        assert result == "milk"
    
    def test_find_matching_item_found(self):
        """Test finding a matching item when one exists."""
        matcher = ItemMatcher({}, " : ")
        
        og_items = [
            {"id": "item1", "value": "Milk : 1 gallon"},
            {"id": "item2", "value": "Eggs"}
        ]
        
        result = matcher.find_matching_item("Milk", og_items)
        
        assert result == {"id": "item1", "value": "Milk : 1 gallon"}
    
    def test_find_matching_item_not_found(self):
        """Test finding a matching item when none exists."""
        matcher = ItemMatcher({}, " : ")
        
        og_items = [
            {"id": "item1", "value": "Milk : 1 gallon"},
            {"id": "item2", "value": "Eggs"}
        ]
        
        result = matcher.find_matching_item("Bread", og_items)
        
        assert result is None
    
    def test_find_matching_item_with_mapping(self):
        """Test finding a matching item with name mapping."""
        matcher = ItemMatcher({"Milk 2%": "Milk (2%)"}, " : ")
        
        og_items = [
            {"id": "item1", "value": "Milk (2%) : 1 gallon"},
            {"id": "item2", "value": "Eggs"}
        ]
        
        result = matcher.find_matching_item("Milk 2%", og_items)
        
        assert result == {"id": "item1", "value": "Milk (2%) : 1 gallon"}
    
    def test_extract_existing_quantity_with_separator(self):
        """Test extracting quantity with separator."""
        matcher = ItemMatcher({}, " : ")
        
        item = {"id": "item1", "value": "Milk : 1 gallon"}
        
        result = matcher.extract_existing_quantity(item)
        
        assert result == "1 gallon"
    
    def test_extract_existing_quantity_with_parentheses(self):
        """Test extracting quantity with parentheses."""
        matcher = ItemMatcher({}, " : ")
        
        item = {"id": "item1", "value": "Milk (1 gallon)"}
        
        result = matcher.extract_existing_quantity(item)
        
        assert result == "1 gallon"
    
    def test_extract_existing_quantity_no_quantity(self):
        """Test extracting quantity with no quantity."""
        matcher = ItemMatcher({}, " : ")
        
        item = {"id": "item1", "value": "Milk"}
        
        result = matcher.extract_existing_quantity(item)
        
        assert result is None
    
    def test_has_quantity_changed_different(self):
        """Test detecting quantity change when different."""
        matcher = ItemMatcher({}, " : ")
        
        assert matcher.has_quantity_changed("1 gallon", "2 gallons") is True
    
    def test_has_quantity_changed_same(self):
        """Test detecting quantity change when same."""
        matcher = ItemMatcher({}, " : ")
        
        assert matcher.has_quantity_changed("1 gallon", "1 gallon") is False
    
    def test_has_quantity_changed_normalized(self):
        """Test detecting quantity change with normalization."""
        matcher = ItemMatcher({}, " : ")
        
        assert matcher.has_quantity_changed("1gallon", "1 gallon") is False
        assert matcher.has_quantity_changed("1 GALLON", "1 gallon") is False

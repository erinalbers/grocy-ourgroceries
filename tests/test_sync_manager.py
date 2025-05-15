"""
Tests for the SyncManager class.
"""

import pytest
from unittest.mock import MagicMock, patch, call

from sync.sync_manager import SyncManager

class TestSyncManager:
    """Test suite for the SyncManager class."""
    
    def test_init(self):
        """Test initialization."""
        grocy_client = MagicMock()
        ourgroceries_client = MagicMock()
        config_manager = MagicMock()
        tracker = MagicMock()
        
        # Mock config_manager methods
        config_manager.get_name_mappings.return_value = {"Milk 2%": "Milk (2%)"}
        config_manager.get_category_mappings.return_value = {"Dairy": "Dairy Products"}
        config_manager.use_categories.return_value = True
        config_manager.get_quantity_separator.return_value = " : "
        config_manager.get_deletion_config.return_value = {"enabled": True}
        
        manager = SyncManager(grocy_client, ourgroceries_client, config_manager, tracker)
        
        assert manager.grocy_client == grocy_client
        assert manager.ourgroceries_client == ourgroceries_client
        assert manager.config_manager == config_manager
        assert manager.tracker == tracker
        assert manager.name_mappings == {"Milk 2%": "Milk (2%)"}
        assert manager.category_mappings == {"Dairy": "Dairy Products"}
        assert manager.use_categories is True
        assert manager.quantity_separator == " : "
    
    def test_map_category_name_with_mapping(self):
        """Test mapping a category name with an existing mapping."""
        manager = self._create_manager()
        manager.category_mappings = {"Dairy": "Dairy Products"}
        
        result = manager.map_category_name("Dairy")
        
        assert result == "Dairy Products"
    
    def test_map_category_name_without_mapping(self):
        """Test mapping a category name without an existing mapping."""
        manager = self._create_manager()
        manager.category_mappings = {"Dairy": "Dairy Products"}
        
        result = manager.map_category_name("Beverages")
        
        assert result == "Beverages"
    
    def test_test_connections_success(self):
        """Test testing connections successfully."""
        manager = self._create_manager()
        
        # Mock client test_connection methods
        manager.grocy_client.test_connection.return_value = True
        manager.ourgroceries_client.test_connection.return_value = True
        
        result = manager.test_connections()
        
        assert result is True
        manager.grocy_client.test_connection.assert_called_once()
        manager.ourgroceries_client.test_connection.assert_called_once()
    
    def test_test_connections_grocy_failure(self):
        """Test testing connections with Grocy failure."""
        manager = self._create_manager()
        
        # Mock client test_connection methods
        manager.grocy_client.test_connection.return_value = False
        manager.ourgroceries_client.test_connection.return_value = True
        
        result = manager.test_connections()
        
        assert result is False
        manager.grocy_client.test_connection.assert_called_once()
        manager.ourgroceries_client.test_connection.assert_called_once()
    
    def test_test_connections_ourgroceries_failure(self):
        """Test testing connections with OurGroceries failure."""
        manager = self._create_manager()
        
        # Mock client test_connection methods
        manager.grocy_client.test_connection.return_value = True
        manager.ourgroceries_client.test_connection.return_value = False
        
        result = manager.test_connections()
        
        assert result is False
        manager.grocy_client.test_connection.assert_called_once()
        manager.ourgroceries_client.test_connection.assert_called_once()
    
    def test_sync_list_empty(self):
        """Test syncing an empty list."""
        manager = self._create_manager()
        
        # Mock grocy_client.get_shopping_list_items to return empty list
        manager.grocy_client.get_shopping_list_items.return_value = []
        
        result = manager.sync_list(1, "Shopping List")
        
        assert result is True
        manager.grocy_client.get_shopping_list_items.assert_called_once_with(1)
        manager.ourgroceries_client.get_list_by_name.assert_not_called()
    
    def test_sync_list_list_not_found(self):
        """Test syncing a list that doesn't exist in OurGroceries."""
        manager = self._create_manager()
        
        # Mock grocy_client.get_shopping_list_items to return items
        manager.grocy_client.get_shopping_list_items.return_value = [{"id": "101"}]
        
        # Mock ourgroceries_client.get_list_by_name to return None
        manager.ourgroceries_client.get_list_by_name.return_value = None
        
        result = manager.sync_list(1, "Shopping List")
        
        assert result is False
        manager.grocy_client.get_shopping_list_items.assert_called_once_with(1)
        manager.ourgroceries_client.get_list_by_name.assert_called_once_with("Shopping List")
    
    def test_sync_list_success(self):
        """Test syncing a list successfully."""
        manager = self._create_manager()
        
        # Mock grocy_client.get_shopping_list_items to return items
        grocy_items = [
            {
                "id": "101",
                "product_id": "201",
                "amount": 3,
                "qu_id": "8",
                "done": 0,
                "product_details": {
                    "name": "Water",
                    "category": {"name": "Beverages"}
                }
            }
        ]
        manager.grocy_client.get_shopping_list_items.return_value = grocy_items
        
        # Mock ourgroceries_client.get_list_by_name to return a list
        og_list = {"id": "list1", "name": "Shopping List"}
        manager.ourgroceries_client.get_list_by_name.return_value = og_list
        
        # Mock ourgroceries_client.get_list_items to return items
        og_items = [{"id": "item1", "value": "Milk"}]
        manager.ourgroceries_client.get_list_items.return_value = og_items
        
        # Mock _process_grocy_item
        with patch.object(manager, '_process_grocy_item') as mock_process:
            result = manager.sync_list(1, "Shopping List")
            
            assert result is True
            manager.grocy_client.get_shopping_list_items.assert_called_once_with(1)
            manager.ourgroceries_client.get_list_by_name.assert_called_once_with("Shopping List")
            manager.ourgroceries_client.get_list_items.assert_called_once_with("list1")
            mock_process.assert_called_once_with(grocy_items[0], "list1", og_items, "Shopping List")
            manager.deletion_manager.process_deletions.assert_called_once_with(
                "list1", grocy_items, og_items, manager.item_matcher
            )
    
    def test_sync_list_exception(self):
        """Test syncing a list with an exception."""
        manager = self._create_manager()
        
        # Mock grocy_client.get_shopping_list_items to raise an exception
        manager.grocy_client.get_shopping_list_items.side_effect = Exception("API error")
        
        result = manager.sync_list(1, "Shopping List")
        
        assert result is False
        manager.grocy_client.get_shopping_list_items.assert_called_once_with(1)
    
    def test_process_grocy_item_new_item(self):
        """Test processing a new Grocy item."""
        manager = self._create_manager()
        
        # Mock _get_product_info
        with patch.object(manager, '_get_product_info') as mock_get_info:
            mock_get_info.return_value = ("Water", "Beverages")
            
            # Mock quantity_formatter.format_quantity
            manager.quantity_formatter.format_quantity.return_value = (3, "3 Bottles")
            
            # Mock item_matcher.map_item_name
            manager.item_matcher.map_item_name.return_value = "Water"
            
            # Mock item_matcher.find_matching_item to return None (no existing item)
            manager.item_matcher.find_matching_item.return_value = None
            
            # Mock _add_new_item
            with patch.object(manager, '_add_new_item') as mock_add:
                grocy_item = {"id": "101"}
                og_list_id = "list1"
                og_items = []
                og_list_name = "Shopping List"
                
                manager._process_grocy_item(grocy_item, og_list_id, og_items, og_list_name)
                
                mock_get_info.assert_called_once_with(grocy_item)
                manager.quantity_formatter.format_quantity.assert_called_once_with(grocy_item)
                manager.item_matcher.map_item_name.assert_called_once_with("Water")
                manager.item_matcher.find_matching_item.assert_called_once_with("Water", og_items)
                mock_add.assert_called_once_with(og_list_id, "Water", "3 Bottles", "Beverages", og_list_name)
    
    def test_process_grocy_item_existing_item(self):
        """Test processing an existing Grocy item."""
        manager = self._create_manager()
        
        # Mock _get_product_info
        with patch.object(manager, '_get_product_info') as mock_get_info:
            mock_get_info.return_value = ("Water", "Beverages")
            
            # Mock quantity_formatter.format_quantity
            manager.quantity_formatter.format_quantity.return_value = (3, "3 Bottles")
            
            # Mock item_matcher.map_item_name
            manager.item_matcher.map_item_name.return_value = "Water"
            
            # Mock item_matcher.find_matching_item to return an existing item
            existing_item = {"id": "item1", "value": "Water : 2 Bottles"}
            manager.item_matcher.find_matching_item.return_value = existing_item
            
            # Mock _update_existing_item
            with patch.object(manager, '_update_existing_item') as mock_update:
                grocy_item = {"id": "101"}
                og_list_id = "list1"
                og_items = [existing_item]
                og_list_name = "Shopping List"
                
                manager._process_grocy_item(grocy_item, og_list_id, og_items, og_list_name)
                
                mock_get_info.assert_called_once_with(grocy_item)
                manager.quantity_formatter.format_quantity.assert_called_once_with(grocy_item)
                manager.item_matcher.map_item_name.assert_called_once_with("Water")
                manager.item_matcher.find_matching_item.assert_called_once_with("Water", og_items)
                mock_update.assert_called_once_with(
                    existing_item, "Water", "3 Bottles", "Beverages", og_list_id, og_list_name
                )
    
    def test_get_product_info_with_product_details(self):
        """Test getting product info with product details."""
        manager = self._create_manager()
        
        grocy_item = {
            "product_details": {
                "name": "Water",
                "category": {"name": "Beverages"}
            }
        }
        
        product_name, category_name = manager._get_product_info(grocy_item)
        
        assert product_name == "Water"
        assert category_name == "Beverages"
    
    def test_get_product_info_with_product_details_no_category(self):
        """Test getting product info with product details but no category."""
        manager = self._create_manager()
        
        grocy_item = {
            "product_details": {
                "name": "Water"
                # No category
            }
        }
        
        product_name, category_name = manager._get_product_info(grocy_item)
        
        assert product_name == "Water"
        assert category_name is None
    
    def test_get_product_info_without_product_details(self):
        """Test getting product info without product details."""
        manager = self._create_manager()
        
        grocy_item = {
            "note": "Water"
            # No product_details
        }
        
        product_name, category_name = manager._get_product_info(grocy_item)
        
        assert product_name == "Water"
        assert category_name is None
    
    def test_get_product_info_without_product_details_or_note(self):
        """Test getting product info without product details or note."""
        manager = self._create_manager()
        
        grocy_item = {
            # No product_details or note
        }
        
        product_name, category_name = manager._get_product_info(grocy_item)
        
        assert product_name == "Unknown item"
        assert category_name is None
    
    def test_update_existing_item_quantity_changed(self):
        """Test updating an existing item when quantity has changed."""
        manager = self._create_manager()
        
        # Mock item_matcher.extract_existing_quantity
        manager.item_matcher.extract_existing_quantity.return_value = "2 Bottles"
        
        # Mock item_matcher.has_quantity_changed
        manager.item_matcher.has_quantity_changed.return_value = True
        
        # Mock ourgroceries_client.remove_item_from_list
        manager.ourgroceries_client.remove_item_from_list.return_value = True
        
        # Mock ourgroceries_client.add_item_to_list
        manager.ourgroceries_client.add_item_to_list.return_value = True
        
        # Mock ourgroceries_client.get_last_added_item_id
        manager.ourgroceries_client.get_last_added_item_id.return_value = "item2"
        
        existing_item = {"id": "item1", "value": "Water : 2 Bottles"}
        og_item_name = "Water"
        quantity_str = "3 Bottles"
        category_name = "Beverages"
        og_list_id = "list1"
        og_list_name = "Shopping List"
        
        manager._update_existing_item(
            existing_item, og_item_name, quantity_str, category_name, og_list_id, og_list_name
        )
        
        manager.item_matcher.extract_existing_quantity.assert_called_once_with(existing_item)
        manager.item_matcher.has_quantity_changed.assert_called_once_with("2 Bottles", "3 Bottles")
        manager.ourgroceries_client.remove_item_from_list.assert_called_once_with(og_list_id, "item1")
        manager.ourgroceries_client.add_item_to_list.assert_called_once_with(
            og_list_id, og_item_name, quantity_str, category_name
        )
        manager.ourgroceries_client.get_last_added_item_id.assert_called_once()
        manager.tracker.track_item.assert_called_once_with(og_list_id, "item2", og_item_name)
    
    def test_update_existing_item_quantity_unchanged(self):
        """Test updating an existing item when quantity has not changed."""
        manager = self._create_manager()
        
        # Mock item_matcher.extract_existing_quantity
        manager.item_matcher.extract_existing_quantity.return_value = "3 Bottles"
        
        # Mock item_matcher.has_quantity_changed
        manager.item_matcher.has_quantity_changed.return_value = False
        
        existing_item = {"id": "item1", "value": "Water : 3 Bottles"}
        og_item_name = "Water"
        quantity_str = "3 Bottles"
        category_name = "Beverages"
        og_list_id = "list1"
        og_list_name = "Shopping List"
        
        manager._update_existing_item(
            existing_item, og_item_name, quantity_str, category_name, og_list_id, og_list_name
        )
        
        manager.item_matcher.extract_existing_quantity.assert_called_once_with(existing_item)
        manager.item_matcher.has_quantity_changed.assert_called_once_with("3 Bottles", "3 Bottles")
        manager.ourgroceries_client.remove_item_from_list.assert_not_called()
        manager.ourgroceries_client.add_item_to_list.assert_not_called()
    
    def test_update_existing_item_remove_failure(self):
        """Test updating an existing item when removal fails."""
        manager = self._create_manager()
        
        # Mock item_matcher.extract_existing_quantity
        manager.item_matcher.extract_existing_quantity.return_value = "2 Bottles"
        
        # Mock item_matcher.has_quantity_changed
        manager.item_matcher.has_quantity_changed.return_value = True
        
        # Mock ourgroceries_client.remove_item_from_list to fail
        manager.ourgroceries_client.remove_item_from_list.return_value = False
        
        existing_item = {"id": "item1", "value": "Water : 2 Bottles"}
        og_item_name = "Water"
        quantity_str = "3 Bottles"
        category_name = "Beverages"
        og_list_id = "list1"
        og_list_name = "Shopping List"
        
        manager._update_existing_item(
            existing_item, og_item_name, quantity_str, category_name, og_list_id, og_list_name
        )
        
        manager.item_matcher.extract_existing_quantity.assert_called_once_with(existing_item)
        manager.item_matcher.has_quantity_changed.assert_called_once_with("2 Bottles", "3 Bottles")
        manager.ourgroceries_client.remove_item_from_list.assert_called_once_with(og_list_id, "item1")
        manager.ourgroceries_client.add_item_to_list.assert_not_called()
    
    def test_add_new_item_success(self):
        """Test adding a new item successfully."""
        manager = self._create_manager()
        
        # Mock ourgroceries_client.add_item_to_list
        manager.ourgroceries_client.add_item_to_list.return_value = True
        
        # Mock ourgroceries_client.get_last_added_item_id
        manager.ourgroceries_client.get_last_added_item_id.return_value = "item1"
        
        og_list_id = "list1"
        og_item_name = "Water"
        quantity_str = "3 Bottles"
        category_name = "Beverages"
        og_list_name = "Shopping List"
        
        manager._add_new_item(og_list_id, og_item_name, quantity_str, category_name, og_list_name)
        
        manager.ourgroceries_client.add_item_to_list.assert_called_once_with(
            og_list_id, og_item_name, quantity_str, category_name
        )
        manager.ourgroceries_client.get_last_added_item_id.assert_called_once()
        manager.tracker.track_item.assert_called_once_with(og_list_id, "item1", og_item_name)
    
    def test_add_new_item_failure(self):
        """Test adding a new item with failure."""
        manager = self._create_manager()
        
        # Mock ourgroceries_client.add_item_to_list to fail
        manager.ourgroceries_client.add_item_to_list.return_value = False
        
        og_list_id = "list1"
        og_item_name = "Water"
        quantity_str = "3 Bottles"
        category_name = "Beverages"
        og_list_name = "Shopping List"
        
        manager._add_new_item(og_list_id, og_item_name, quantity_str, category_name, og_list_name)
        
        manager.ourgroceries_client.add_item_to_list.assert_called_once_with(
            og_list_id, og_item_name, quantity_str, category_name
        )
        manager.ourgroceries_client.get_last_added_item_id.assert_not_called()
        manager.tracker.track_item.assert_not_called()
    
    def test_sync_all_lists_success(self):
        """Test syncing all lists successfully."""
        manager = self._create_manager()
        
        # Mock test_connections
        with patch.object(manager, 'test_connections') as mock_test:
            mock_test.return_value = True
            
            # Mock sync_list
            with patch.object(manager, 'sync_list') as mock_sync:
                mock_sync.return_value = True
                
                # Mock config_manager.get_list_mappings
                manager.config_manager.get_list_mappings.return_value = [
                    {"grocy_list_id": 1, "ourgroceries_list_name": "Shopping List"},
                    {"grocy_list_id": 2, "ourgroceries_list_name": "Pet Supplies"}
                ]
                
                result = manager.sync_all_lists()
                
                assert result is True
                mock_test.assert_called_once()
                assert mock_sync.call_count == 2
                mock_sync.assert_has_calls([
                    call(1, "Shopping List"),
                    call(2, "Pet Supplies")
                ])
    
    def test_sync_all_lists_connection_failure(self):
        """Test syncing all lists with connection failure."""
        manager = self._create_manager()
        
        # Mock test_connections to fail
        with patch.object(manager, 'test_connections') as mock_test:
            mock_test.return_value = False
            
            # Mock sync_list
            with patch.object(manager, 'sync_list') as mock_sync:
                result = manager.sync_all_lists()
                
                assert result is False
                mock_test.assert_called_once()
                mock_sync.assert_not_called()
    
    def test_sync_all_lists_partial_failure(self):
        """Test syncing all lists with partial failure."""
        manager = self._create_manager()
        
        # Mock test_connections
        with patch.object(manager, 'test_connections') as mock_test:
            mock_test.return_value = True
            
            # Mock sync_list to succeed for first list and fail for second
            with patch.object(manager, 'sync_list') as mock_sync:
                mock_sync.side_effect = [True, False]
                
                # Mock config_manager.get_list_mappings
                manager.config_manager.get_list_mappings.return_value = [
                    {"grocy_list_id": 1, "ourgroceries_list_name": "Shopping List"},
                    {"grocy_list_id": 2, "ourgroceries_list_name": "Pet Supplies"}
                ]
                
                result = manager.sync_all_lists()
                
                assert result is False
                mock_test.assert_called_once()
                assert mock_sync.call_count == 2
                mock_sync.assert_has_calls([
                    call(1, "Shopping List"),
                    call(2, "Pet Supplies")
                ])
    
    def _create_manager(self):
        """Helper method to create a SyncManager with mocks."""
        grocy_client = MagicMock()
        ourgroceries_client = MagicMock()
        config_manager = MagicMock()
        tracker = MagicMock()
        
        # Create manager with mocked dependencies
        manager = SyncManager(grocy_client, ourgroceries_client, config_manager, tracker)
        
        # Mock the helper classes
        manager.item_matcher = MagicMock()
        manager.quantity_formatter = MagicMock()
        manager.deletion_manager = MagicMock()
        
        return manager

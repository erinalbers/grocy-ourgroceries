"""
Tests for the DeletionManager class.
"""

import pytest
from unittest.mock import MagicMock, patch

from sync.deletion_manager import DeletionManager

class TestDeletionManager:
    """Test suite for the DeletionManager class."""
    
    def test_init(self):
        """Test initialization."""
        ourgroceries_client = MagicMock()
        tracker = MagicMock()
        config = {
            "enabled": True,
            "dry_run": False,
            "respect_crossed_off": True,
            "preserve_manual_items": True
        }
        
        manager = DeletionManager(ourgroceries_client, tracker, config)
        
        assert manager.ourgroceries_client == ourgroceries_client
        assert manager.tracker == tracker
        assert manager.enabled is True
        assert manager.dry_run is False
        assert manager.respect_crossed_off is True
        assert manager.preserve_manual_items is True
    
    def test_process_deletions_disabled(self):
        """Test process_deletions when deletion is disabled."""
        ourgroceries_client = MagicMock()
        tracker = MagicMock()
        config = {
            "enabled": False
        }
        
        manager = DeletionManager(ourgroceries_client, tracker, config)
        item_matcher = MagicMock()
        
        # Call process_deletions
        manager.process_deletions("list1", [], [], item_matcher)
        
        # Verify no actions were taken
        ourgroceries_client.remove_item_from_list.assert_not_called()
        tracker.remove_tracking.assert_not_called()
    
    def test_process_deletions_no_items_to_remove(self):
        """Test process_deletions when there are no items to remove."""
        ourgroceries_client = MagicMock()
        tracker = MagicMock()
        config = {
            "enabled": True,
            "dry_run": False
        }
        
        manager = DeletionManager(ourgroceries_client, tracker, config)
        
        # Mock item_matcher
        item_matcher = MagicMock()
        item_matcher.map_item_name.return_value = "Water"
        item_matcher.extract_base_name.return_value = "water"
        
        # Set up test data
        grocy_items = [
            {
                "product_details": {"name": "Water"},
                "done": 0
            }
        ]
        
        og_items = [
            {
                "id": "item1",
                "value": "Water : 3 Bottles"
            }
        ]
        
        # Call process_deletions
        manager.process_deletions("list1", grocy_items, og_items, item_matcher)
        
        # Verify no items were removed
        ourgroceries_client.remove_item_from_list.assert_not_called()
        tracker.remove_tracking.assert_not_called()
    
    def test_process_deletions_with_items_to_remove(self):
        """Test process_deletions when there are items to remove."""
        ourgroceries_client = MagicMock()
        tracker = MagicMock()
        config = {
            "enabled": True,
            "dry_run": False,
            "respect_crossed_off": False,
            "preserve_manual_items": False
        }
        
        manager = DeletionManager(ourgroceries_client, tracker, config)
        
        # Mock item_matcher
        item_matcher = MagicMock()
        item_matcher.map_item_name.side_effect = lambda name: name  # Return the same name
        item_matcher.extract_base_name.return_value = "eggs"  # Different from grocy items
        
        # Set up test data
        grocy_items = [
            {
                "product_details": {"name": "Water"},
                "done": 0
            }
        ]
        
        og_items = [
            {
                "id": "item1",
                "value": "Eggs : 12"
            }
        ]
        
        # Mock successful removal
        ourgroceries_client.remove_item_from_list.return_value = True
        
        # Call process_deletions
        manager.process_deletions("list1", grocy_items, og_items, item_matcher)
        
        # Verify item was removed
        ourgroceries_client.remove_item_from_list.assert_called_once_with("list1", "item1")
        tracker.remove_tracking.assert_called_once_with("list1", "item1")
    
    def test_process_deletions_dry_run(self):
        """Test process_deletions in dry run mode."""
        ourgroceries_client = MagicMock()
        tracker = MagicMock()
        config = {
            "enabled": True,
            "dry_run": True,
            "respect_crossed_off": False,
            "preserve_manual_items": False
        }
        
        manager = DeletionManager(ourgroceries_client, tracker, config)
        
        # Mock item_matcher
        item_matcher = MagicMock()
        item_matcher.map_item_name.side_effect = lambda name: name  # Return the same name
        item_matcher.extract_base_name.return_value = "eggs"  # Different from grocy items
        
        # Set up test data
        grocy_items = [
            {
                "product_details": {"name": "Water"},
                "done": 0
            }
        ]
        
        og_items = [
            {
                "id": "item1",
                "value": "Eggs : 12"
            }
        ]
        
        # Call process_deletions
        manager.process_deletions("list1", grocy_items, og_items, item_matcher)
        
        # Verify no actual removal happened in dry run mode
        ourgroceries_client.remove_item_from_list.assert_not_called()
        tracker.remove_tracking.assert_not_called()
    
    def test_process_deletions_respect_crossed_off(self):
        """Test process_deletions respecting crossed off items."""
        ourgroceries_client = MagicMock()
        tracker = MagicMock()
        config = {
            "enabled": True,
            "dry_run": False,
            "respect_crossed_off": True,
            "preserve_manual_items": False
        }
        
        manager = DeletionManager(ourgroceries_client, tracker, config)
        
        # Mock item_matcher
        item_matcher = MagicMock()
        item_matcher.map_item_name.side_effect = lambda name: name  # Return the same name
        item_matcher.extract_base_name.return_value = "eggs"  # Different from grocy items
        
        # Set up test data
        grocy_items = [
            {
                "product_details": {"name": "Water"},
                "done": 0
            }
        ]
        
        og_items = [
            {
                "id": "item1",
                "value": "Eggs : 12",
                "crossedOff": True  # Item is crossed off
            }
        ]
        
        # Call process_deletions
        manager.process_deletions("list1", grocy_items, og_items, item_matcher)
        
        # Verify crossed off item was not removed
        ourgroceries_client.remove_item_from_list.assert_not_called()
        tracker.remove_tracking.assert_not_called()
    
    def test_process_deletions_preserve_manual_items(self):
        """Test process_deletions preserving manually added items."""
        ourgroceries_client = MagicMock()
        tracker = MagicMock()
        config = {
            "enabled": True,
            "dry_run": False,
            "respect_crossed_off": False,
            "preserve_manual_items": True
        }
        
        manager = DeletionManager(ourgroceries_client, tracker, config)
        
        # Mock item_matcher
        item_matcher = MagicMock()
        item_matcher.map_item_name.side_effect = lambda name: name  # Return the same name
        item_matcher.extract_base_name.return_value = "eggs"  # Different from grocy items
        
        # Set up test data
        grocy_items = [
            {
                "product_details": {"name": "Water"},
                "done": 0
            }
        ]
        
        og_items = [
            {
                "id": "item1",
                "value": "Eggs : 12"
            }
        ]
        
        # Mock tracker to indicate item was not tracked (manually added)
        tracker.is_tracked_item.return_value = False
        
        # Call process_deletions
        manager.process_deletions("list1", grocy_items, og_items, item_matcher)
        
        # Verify manually added item was not removed
        tracker.is_tracked_item.assert_called_once_with("list1", "item1")
        ourgroceries_client.remove_item_from_list.assert_not_called()
        tracker.remove_tracking.assert_not_called()
    
    def test_process_deletions_removal_failure(self):
        """Test process_deletions when removal fails."""
        ourgroceries_client = MagicMock()
        tracker = MagicMock()
        config = {
            "enabled": True,
            "dry_run": False,
            "respect_crossed_off": False,
            "preserve_manual_items": False
        }
        
        manager = DeletionManager(ourgroceries_client, tracker, config)
        
        # Mock item_matcher
        item_matcher = MagicMock()
        item_matcher.map_item_name.side_effect = lambda name: name  # Return the same name
        item_matcher.extract_base_name.return_value = "eggs"  # Different from grocy items
        
        # Set up test data
        grocy_items = [
            {
                "product_details": {"name": "Water"},
                "done": 0
            }
        ]
        
        og_items = [
            {
                "id": "item1",
                "value": "Eggs : 12"
            }
        ]
        
        # Mock failed removal
        ourgroceries_client.remove_item_from_list.return_value = False
        
        # Call process_deletions
        manager.process_deletions("list1", grocy_items, og_items, item_matcher)
        
        # Verify removal was attempted but tracking was not removed
        ourgroceries_client.remove_item_from_list.assert_called_once_with("list1", "item1")
        tracker.remove_tracking.assert_not_called()

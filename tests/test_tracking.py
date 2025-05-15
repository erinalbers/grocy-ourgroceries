"""
Tests for the SyncTracker class.
"""

import pytest
import os
import json
from unittest.mock import MagicMock, patch, mock_open

from utils.tracking import SyncTracker

class TestSyncTracker:
    """Test suite for the SyncTracker class."""
    
    def test_init_new_file(self):
        """Test initialization with a new tracking file."""
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = False
            
            tracker = SyncTracker('test_tracking.json')
            
            assert tracker.tracking_file == 'test_tracking.json'
            assert tracker.tracking_data == {"lists": {}}
    
    def test_init_existing_file(self):
        """Test initialization with an existing tracking file."""
        test_data = {"lists": {"list1": ["item1", "item2"]}}
        
        with patch('os.path.exists') as mock_exists, \
             patch('builtins.open', mock_open(read_data=json.dumps(test_data))) as mock_file:
            mock_exists.return_value = True
            
            tracker = SyncTracker('test_tracking.json')
            
            assert tracker.tracking_file == 'test_tracking.json'
            assert tracker.tracking_data == test_data
            mock_file.assert_called_once_with('test_tracking.json', 'r')
    
    def test_init_file_error(self):
        """Test initialization with a file error."""
        with patch('os.path.exists') as mock_exists, \
             patch('builtins.open') as mock_file:
            mock_exists.return_value = True
            mock_file.side_effect = Exception("File error")
            
            tracker = SyncTracker('test_tracking.json')
            
            assert tracker.tracking_file == 'test_tracking.json'
            assert tracker.tracking_data == {"lists": {}}
    
    def test_save_tracking_data(self):
        """Test saving tracking data."""
        test_data = {"lists": {"list1": ["item1", "item2"]}}
        
        with patch('builtins.open', mock_open()) as mock_file:
            tracker = SyncTracker('test_tracking.json')
            tracker.tracking_data = test_data
            
            tracker._save_tracking_data()
            
            mock_file.assert_called_once_with('test_tracking.json', 'w')
            handle = mock_file()
            assert handle.write.called
            
            # If you want to verify the content, join all the write calls
            written_data = ''.join(call_args[0][0] for call_args in handle.write.call_args_list)
            assert json.loads(written_data) == test_data
    
    def test_save_tracking_data_error(self):
        """Test saving tracking data with an error."""
        with patch('builtins.open') as mock_file:
            mock_file.side_effect = Exception("File error")
            
            tracker = SyncTracker('test_tracking.json')
            
            # This should not raise an exception
            tracker._save_tracking_data()
    
    def test_track_item_new_list(self):
        """Test tracking an item for a new list."""
        with patch.object(SyncTracker, '_save_tracking_data') as mock_save:
            tracker = SyncTracker('test_tracking.json')
            
            tracker.track_item("list1", "item1", "Water")
            
            assert "list1" in tracker.tracking_data["lists"]
            assert "item1" in tracker.tracking_data["lists"]["list1"]
            mock_save.assert_called_once()
    
    def test_track_item_existing_list(self):
        """Test tracking an item for an existing list."""
        with patch.object(SyncTracker, '_save_tracking_data') as mock_save:
            tracker = SyncTracker('test_tracking.json')
            tracker.tracking_data = {"lists": {"list1": ["item2"]}}
            
            tracker.track_item("list1", "item1", "Water")
            
            assert "list1" in tracker.tracking_data["lists"]
            assert "item1" in tracker.tracking_data["lists"]["list1"]
            assert "item2" in tracker.tracking_data["lists"]["list1"]
            mock_save.assert_called_once()
    
    def test_track_item_already_tracked(self):
        """Test tracking an item that is already tracked."""
        with patch.object(SyncTracker, '_save_tracking_data') as mock_save:
            tracker = SyncTracker('test_tracking.json')
            tracker.tracking_data = {"lists": {"list1": ["item1"]}}
            
            tracker.track_item("list1", "item1", "Water")
            
            assert "list1" in tracker.tracking_data["lists"]
            assert "item1" in tracker.tracking_data["lists"]["list1"]
            mock_save.assert_not_called()  # Should not save if item is already tracked
    
    def test_is_tracked_item_true(self):
        """Test checking if an item is tracked (true case)."""
        tracker = SyncTracker('test_tracking.json')
        tracker.tracking_data = {"lists": {"list1": ["item1"]}}
        
        result = tracker.is_tracked_item("list1", "item1")
        
        assert result is True
    
    def test_is_tracked_item_false_wrong_list(self):
        """Test checking if an item is tracked with wrong list (false case)."""
        tracker = SyncTracker('test_tracking.json')
        tracker.tracking_data = {"lists": {"list1": ["item1"]}}
        
        result = tracker.is_tracked_item("list2", "item1")
        
        assert result is False
    
    def test_is_tracked_item_false_wrong_item(self):
        """Test checking if an item is tracked with wrong item (false case)."""
        tracker = SyncTracker('test_tracking.json')
        tracker.tracking_data = {"lists": {"list1": ["item1"]}}
        
        result = tracker.is_tracked_item("list1", "item2")
        
        assert result is False
    
    def test_remove_tracking_success(self):
        """Test removing tracking for an item (success case)."""
        with patch.object(SyncTracker, '_save_tracking_data') as mock_save:
            tracker = SyncTracker('test_tracking.json')
            tracker.tracking_data = {"lists": {"list1": ["item1", "item2"]}}
            
            tracker.remove_tracking("list1", "item1")
            
            assert "list1" in tracker.tracking_data["lists"]
            assert "item1" not in tracker.tracking_data["lists"]["list1"]
            assert "item2" in tracker.tracking_data["lists"]["list1"]
            mock_save.assert_called_once()
    
    def test_remove_tracking_wrong_list(self):
        """Test removing tracking for an item with wrong list."""
        with patch.object(SyncTracker, '_save_tracking_data') as mock_save:
            tracker = SyncTracker('test_tracking.json')
            tracker.tracking_data = {"lists": {"list1": ["item1"]}}
            
            tracker.remove_tracking("list2", "item1")
            
            assert "list1" in tracker.tracking_data["lists"]
            assert "item1" in tracker.tracking_data["lists"]["list1"]
            mock_save.assert_not_called()
    
    def test_remove_tracking_wrong_item(self):
        """Test removing tracking for an item with wrong item."""
        with patch.object(SyncTracker, '_save_tracking_data') as mock_save:
            tracker = SyncTracker('test_tracking.json')
            tracker.tracking_data = {"lists": {"list1": ["item1"]}}
            
            tracker.remove_tracking("list1", "item2")
            
            assert "list1" in tracker.tracking_data["lists"]
            assert "item1" in tracker.tracking_data["lists"]["list1"]
            mock_save.assert_not_called()

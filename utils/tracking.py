"""
Sync tracking utility for Grocy-OurGroceries sync.
Tracks which items were added or updated by the sync tool.
"""

import os
import json
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class SyncTracker:
    def __init__(self, tracking_file: str = 'sync_tracking.json'):
        """
        Initialize the sync tracker.
        
        Args:
            tracking_file: Path to the tracking data file
        """
        self.tracking_file = tracking_file
        self.tracking_data = self._load_tracking_data()
    
    def _load_tracking_data(self) -> Dict[str, Dict[str, List[str]]]:
        """
        Load tracking data from file.
        
        Returns:
            The tracking data as a dictionary
        """
        try:
            if os.path.exists(self.tracking_file):
                with open(self.tracking_file, 'r') as f:
                    return json.load(f)
            else:
                return {"lists": {}}
        except Exception as e:
            logger.error(f"Failed to load tracking data: {e}")
            return {"lists": {}}
    
    def _save_tracking_data(self):
        """Save tracking data to file."""
        try:
            with open(self.tracking_file, 'w') as f:
                json.dump(self.tracking_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save tracking data: {e}")
    
    def track_item(self, list_id: str, item_id: str, item_name: str):
        """
        Track an item that was added or updated by the sync tool.
        
        Args:
            list_id: The ID of the OurGroceries list
            item_id: The ID of the item
            item_name: The name of the item
        """
        if list_id not in self.tracking_data["lists"]:
            self.tracking_data["lists"][list_id] = []
        
        # Store the item ID
        if item_id not in self.tracking_data["lists"][list_id]:
            self.tracking_data["lists"][list_id].append(item_id)
            self._save_tracking_data()
    
    def is_tracked_item(self, list_id: str, item_id: str) -> bool:
        """
        Check if an item is tracked by the sync tool.
        
        Args:
            list_id: The ID of the OurGroceries list
            item_id: The ID of the item
            
        Returns:
            True if the item is tracked, False otherwise
        """
        return (list_id in self.tracking_data["lists"] and 
                item_id in self.tracking_data["lists"][list_id])
    
    def remove_tracking(self, list_id: str, item_id: str):
        """
        Remove an item from tracking.
        
        Args:
            list_id: The ID of the OurGroceries list
            item_id: The ID of the item
        """
        if list_id in self.tracking_data["lists"] and item_id in self.tracking_data["lists"][list_id]:
            self.tracking_data["lists"][list_id].remove(item_id)
            self._save_tracking_data()

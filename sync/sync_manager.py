"""
Sync manager for Grocy-OurGroceries sync.
Handles synchronization of shopping lists from Grocy to OurGroceries.
"""

import logging
import json
import traceback
from typing import Dict, List, Any, Optional

from sync.item_matcher import ItemMatcher
from sync.quantity_formatter import QuantityFormatter
from sync.deletion_manager import DeletionManager
from utils.tracking import SyncTracker

logger = logging.getLogger(__name__)

class SyncManager:
    def __init__(self, grocy_client, ourgroceries_client, config_manager, tracker=None):
        """
        Initialize the sync manager.
        
        Args:
            grocy_client: Initialized Grocy API client
            ourgroceries_client: Initialized OurGroceries API client
            config_manager: Configuration manager
            tracker: Optional SyncTracker instance
        """
        self.grocy_client = grocy_client
        self.ourgroceries_client = ourgroceries_client
        self.config_manager = config_manager
        
        # Get configuration
        self.name_mappings = config_manager.get_name_mappings()
        self.category_mappings = config_manager.get_category_mappings()
        self.use_categories = config_manager.use_categories()
        self.quantity_separator = config_manager.get_quantity_separator()
        
        # Initialize helper classes
        self.tracker = tracker or SyncTracker(
            config_manager.get_deletion_config().get('tracking_file', 'sync_tracking.json')
        )
        self.item_matcher = ItemMatcher(self.name_mappings, self.quantity_separator)
        self.quantity_formatter = QuantityFormatter(grocy_client, self.quantity_separator)
        self.deletion_manager = DeletionManager(
            ourgroceries_client, 
            self.tracker, 
            config_manager.get_deletion_config()
        )
    
    def map_category_name(self, grocy_category: str) -> str:
        """
        Map a Grocy category name to an OurGroceries category name.
        
        Args:
            grocy_category: The name of the category in Grocy
            
        Returns:
            The mapped name for OurGroceries
        """
        if grocy_category in self.category_mappings:
            return self.category_mappings[grocy_category]
        return grocy_category
    
    def test_connections(self) -> bool:
        """
        Test connections to both Grocy and OurGroceries.
        
        Returns:
            True if both connections are successful, False otherwise
        """
        grocy_ok = self.grocy_client.test_connection()
        og_ok = self.ourgroceries_client.test_connection()
        
        if grocy_ok and og_ok:
            logger.info("Successfully connected to both Grocy and OurGroceries")
            return True
        else:
            if not grocy_ok:
                logger.error("Failed to connect to Grocy")
            if not og_ok:
                logger.error("Failed to connect to OurGroceries")
            return False
    
    def sync_list(self, grocy_list_id: int, ourgroceries_list_name: str) -> bool:
        """
        Synchronize a single shopping list from Grocy to OurGroceries.
        
        Args:
            grocy_list_id: The ID of the Grocy shopping list
            ourgroceries_list_name: The name of the OurGroceries list
            
        Returns:
            True if sync was successful, False otherwise
        """
        try:
            # Get items from Grocy
            logger.debug(f"Fetching items from Grocy list {grocy_list_id}")
            grocy_items = self.grocy_client.get_shopping_list_items(grocy_list_id)
            if not grocy_items:
                logger.warning(f"No items found in Grocy list {grocy_list_id}")
                return True  # Not an error, just empty
            
            # Find OurGroceries list
            logger.debug(f"Finding OurGroceries list '{ourgroceries_list_name}'")
            og_list = self.ourgroceries_client.get_list_by_name(ourgroceries_list_name)
            if not og_list:
                logger.error(f"OurGroceries list '{ourgroceries_list_name}' not found")
                return False
            
            og_list_id = og_list['id']
            logger.debug(f"Found OurGroceries list with ID: {og_list_id}")
            
            # Get current items in OurGroceries list
            logger.debug(f"Fetching items from OurGroceries list {og_list_id}")
            og_items = self.ourgroceries_client.get_list_items(og_list_id)
            logger.debug(f"Found {len(og_items)} items in OurGroceries list")
            
            # Process each Grocy item
            for grocy_item in grocy_items:
                # Skip completed items
                if grocy_item.get('done', 0) == 1:
                    continue
                
                # Process the item
                self._process_grocy_item(grocy_item, og_list_id, og_items, ourgroceries_list_name)
            
            # Process deletions if enabled
            self.deletion_manager.process_deletions(og_list_id, grocy_items, og_items, self.item_matcher)
            
            return True
            
        except Exception as e:
            logger.error(f"Error syncing list {grocy_list_id} to {ourgroceries_list_name}: {e}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            return False
    
    def _process_grocy_item(self, grocy_item: Dict[str, Any], og_list_id: str, 
                           og_items: List[Dict[str, Any]], ourgroceries_list_name: str):
        """
        Process a single Grocy item.
        
        Args:
            grocy_item: The item from Grocy
            og_list_id: The ID of the OurGroceries list
            og_items: The current items in the OurGroceries list
            ourgroceries_list_name: The name of the OurGroceries list
        """
        # Log the raw item data for debugging
        logger.info(f"DEBUG - Raw Grocy item data: {json.dumps(grocy_item, default=str, indent=2)}")
        
        # Get product name and category
        product_name, category_name = self._get_product_info(grocy_item)
        
        # Format quantity
        quantity_value, quantity_str = self.quantity_formatter.format_quantity(grocy_item)
        logger.info(f"DEBUG - After formatting: product_name={product_name}, quantity_value={quantity_value}, quantity_str={quantity_str}")
        
        # Map the product name if needed
        og_item_name = self.item_matcher.map_item_name(product_name)
        
        # Check if this item or a similar one already exists
        existing_item = self.item_matcher.find_matching_item(product_name, og_items)
        
        if existing_item:
            self._update_existing_item(existing_item, og_item_name, quantity_str, 
                                     category_name, og_list_id, ourgroceries_list_name)
        else:
            self._add_new_item(og_list_id, og_item_name, quantity_str, 
                              category_name, ourgroceries_list_name)
    
    def _get_product_info(self, grocy_item: Dict[str, Any]) -> tuple:
        """
        Extract product name and category from Grocy item.
        
        Args:
            grocy_item: The item from Grocy
            
        Returns:
            A tuple of (product_name, category_name)
        """
        product_name = None
        category_name = None
        
        if 'product_details' in grocy_item and grocy_item['product_details']:
            product = grocy_item['product_details']
            product_name = product.get('name')
            
            # Get category if available
            if 'category' in product and product['category'] and self.use_categories:
                grocy_category = product['category'].get('name')
                if grocy_category:
                    category_name = self.map_category_name(grocy_category)
                    logger.debug(f"Using category '{category_name}' for item '{product_name}'")
        else:
            product_name = grocy_item.get('note', 'Unknown item')
        
        return product_name, category_name
    
    def _update_existing_item(self, existing_item: Dict[str, Any], og_item_name: str, 
                             quantity_str: str, category_name: str, og_list_id: str,
                             ourgroceries_list_name: str):
        """
        Update an existing item if needed.
        
        Args:
            existing_item: The existing item in OurGroceries
            og_item_name: The mapped item name for OurGroceries
            quantity_str: The formatted quantity string
            category_name: The category name
            og_list_id: The ID of the OurGroceries list
            ourgroceries_list_name: The name of the OurGroceries list
        """
        # Check if the quantity has changed
        existing_quantity = self.item_matcher.extract_existing_quantity(existing_item)
        
        logger.debug(f"Comparing quantities - existing: '{existing_quantity}', new: '{quantity_str}'")
        
        # Check if the quantity has actually changed (ignoring formatting differences)
        if self.item_matcher.has_quantity_changed(existing_quantity, quantity_str):
            # Quantity has changed, remove the existing item and add it again with the new quantity
            logger.debug(f"Quantity changed from '{existing_quantity}' to '{quantity_str}', updating item")
            
            # Remove the existing item
            success = self.ourgroceries_client.remove_item_from_list(
                og_list_id,
                existing_item['id']
            )
            
            if success:
                logger.debug(f"Removed existing item '{existing_item['value']}' from OurGroceries list")
                
                # Add the item with the new quantity
                success = self.ourgroceries_client.add_item_to_list(
                    og_list_id, 
                    og_item_name,
                    quantity_str,  # Pass quantity separately
                    category_name
                )
                
                if success:
                    # Track the new item
                    new_item_id = self.ourgroceries_client.get_last_added_item_id()
                    if new_item_id:
                        self.tracker.track_item(og_list_id, new_item_id, og_item_name)
                    logger.info(f"Updated item '{og_item_name}' with new quantity '{quantity_str}' in OurGroceries list '{ourgroceries_list_name}'")
                else:
                    logger.error(f"Failed to add updated item '{og_item_name}' to OurGroceries list")
            else:
                logger.error(f"Failed to remove existing item '{existing_item['value']}' from OurGroceries list")
        else:
            logger.debug(f"Item '{og_item_name}' already exists with the same quantity, skipping")
    
    def _add_new_item(self, og_list_id: str, og_item_name: str, quantity_str: str, 
                     category_name: str, ourgroceries_list_name: str):
        """
        Add a new item to the OurGroceries list.
        
        Args:
            og_list_id: The ID of the OurGroceries list
            og_item_name: The mapped item name for OurGroceries
            quantity_str: The formatted quantity string
            category_name: The category name
            ourgroceries_list_name: The name of the OurGroceries list
        """
        logger.debug(f"Adding item '{og_item_name}' with quantity '{quantity_str}' to OurGroceries list")
        
        # Log the final item data for debugging
        final_item_data = {
            "name": og_item_name,
            "quantity": quantity_str,
            "category": category_name
        }
        logger.debug(f"Final item data for OurGroceries: {json.dumps(final_item_data, indent=2)}")
        
        # Add the item to OurGroceries
        success = self.ourgroceries_client.add_item_to_list(
            og_list_id, 
            og_item_name,
            quantity_str,
            category_name
        )
        
        if success:
            # Track the added item
            item_id = self.ourgroceries_client.get_last_added_item_id()
            if item_id:
                self.tracker.track_item(og_list_id, item_id, og_item_name)
                
            category_info = f" in category '{category_name}'" if category_name else ""
            logger.info(f"Added item '{og_item_name}'{category_info} to OurGroceries list '{ourgroceries_list_name}'")
        else:
            logger.error(f"Failed to add item '{og_item_name}' to OurGroceries list")
    
    def sync_all_lists(self) -> bool:
        """
        Synchronize all configured shopping lists.
        
        Returns:
            True if all syncs were successful, False if any failed
        """
        logger.info("Starting sync of all lists")
        
        if not self.test_connections():
            logger.error("Connection test failed, aborting sync")
            return False
        
        success = True
        for list_mapping in self.config_manager.get_list_mappings():
            grocy_list_id = list_mapping['grocy_list_id']
            og_list_name = list_mapping['ourgroceries_list_name']
            
            logger.info(f"Syncing Grocy list {grocy_list_id} to OurGroceries list '{og_list_name}'")
            if not self.sync_list(grocy_list_id, og_list_name):
                success = False
        
        if success:
            logger.info("All lists synced successfully")
        else:
            logger.warning("Some lists failed to sync")
        
        return success

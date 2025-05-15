"""
Deletion manager for Grocy-OurGroceries sync.
Handles deletion of items from OurGroceries that are no longer in Grocy.
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class DeletionManager:
    def __init__(self, ourgroceries_client, tracker, config: Dict[str, Any]):
        """
        Initialize the deletion manager.
        
        Args:
            ourgroceries_client: Initialized OurGroceries API client
            tracker: SyncTracker instance
            config: Deletion configuration
        """
        self.ourgroceries_client = ourgroceries_client
        self.tracker = tracker
        self.enabled = config.get('enabled', False)
        self.dry_run = config.get('dry_run', True)
        self.respect_crossed_off = config.get('respect_crossed_off', True)
        self.preserve_manual_items = config.get('preserve_manual_items', True)
    
    def process_deletions(self, og_list_id: str, grocy_items: List[Dict[str, Any]], 
                         og_items: List[Dict[str, Any]], item_matcher):
        """
        Process deletions from OurGroceries based on what's in Grocy.
        
        Args:
            og_list_id: The OurGroceries list ID
            grocy_items: The items from Grocy
            og_items: The items from OurGroceries
            item_matcher: ItemMatcher instance for name matching
        """
        if not self.enabled:
            return
        
        # Create a set of product names in Grocy (after mapping)
        grocy_product_names = set()
        for grocy_item in grocy_items:
            if grocy_item.get('done', 0) == 1:
                continue  # Skip completed items
                
            product_name = None
            if 'product_details' in grocy_item and grocy_item['product_details']:
                product = grocy_item['product_details']
                product_name = product.get('name')
            else:
                product_name = grocy_item.get('note', 'Unknown item')
                
            # Map the product name if needed
            og_item_name = item_matcher.map_item_name(product_name)
            logger.debug(f"Mapped product name: {product_name} -> {og_item_name}")
            grocy_product_names.add(og_item_name.lower())
        
        # Check each OurGroceries item
        items_to_remove = []
        for og_item in og_items:
            if not isinstance(og_item, dict) or 'id' not in og_item or 'value' not in og_item:
                continue
                
            # Skip crossed off items if configured to do so
            if self.respect_crossed_off and og_item.get('crossedOff', False):
                logger.debug(f"Skipping crossed off item: {og_item['value']}")
                continue
                
            # Skip items not tracked by the sync tool if configured to preserve manual items
            if self.preserve_manual_items and not self.tracker.is_tracked_item(og_list_id, og_item['id']):
                logger.debug(f"Preserving manually added item: {og_item['value']}")
                continue
                
            # Extract the base item name (without quantity)
            base_name = item_matcher.extract_base_name(og_item['value'])
                
            # Check if this item exists in Grocy
            if base_name not in grocy_product_names:
                items_to_remove.append(og_item)
                
        # Process removals
        for item in items_to_remove:
            if self.dry_run:
                logger.info(f"[DRY RUN] Would remove item '{item['value']}' from OurGroceries list")
            else:
                logger.info(f"Removing item '{item['value']}' from OurGroceries list (not in Grocy)")
                success = self.ourgroceries_client.remove_item_from_list(og_list_id, item['id'])
                if success:
                    self.tracker.remove_tracking(og_list_id, item['id'])
                else:
                    logger.error(f"Failed to remove item '{item['value']}' from OurGroceries list")

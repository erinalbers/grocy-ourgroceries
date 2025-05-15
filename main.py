#!/usr/bin/env python3
"""
Main entry point for the Grocy-OurGroceries sync tool.
"""

import argparse
import logging
import time
import schedule
import traceback
import sys

from config.config_manager import ConfigManager
from sync.sync_manager import SyncManager
from utils.tracking import SyncTracker
from clients.grocy_client import GrocyClient
from clients.ourgroceries_client import OurGroceriesClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for the sync tool."""
    parser = argparse.ArgumentParser(description='Sync Grocy shopping lists to OurGroceries')
    parser.add_argument('--config', default='config.json', help='Path to config file')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    try:
        # Initialize configuration
        config_manager = ConfigManager(args.config)
        
        # Initialize clients
        grocy_config = config_manager.get_grocy_config()
        grocy_client = GrocyClient(
            grocy_config['api_url'],
            grocy_config['api_key']
        )
        
        og_config = config_manager.get_ourgroceries_config()
        quantity_separator = config_manager.get_quantity_separator()
        ourgroceries_client = OurGroceriesClient(
            og_config['username'],
            og_config['password'],
            config_manager.get_sync_config().get('category_ids', {}),
            config_manager.get_sync_config().get('default_category_id', ''),
            quantity_separator
        )
        
        # Initialize tracker
        deletion_config = config_manager.get_deletion_config()
        tracker = SyncTracker(deletion_config.get('tracking_file', 'sync_tracking.json'))
        
        # Initialize sync manager
        sync_manager = SyncManager(grocy_client, ourgroceries_client, config_manager, tracker)
        
        if args.once:
            # Run once and exit
            sync_manager.sync_all_lists()
        else:
            # Schedule regular syncs
            interval = config_manager.get_sync_interval()
            
            logger.info(f"Scheduling sync every {interval} minutes")
            schedule.every(interval).minutes.do(sync_manager.sync_all_lists)
            
            # Run once immediately
            sync_manager.sync_all_lists()
            
            # Keep running
            while True:
                schedule.run_pending()
                time.sleep(1)
                
    except KeyboardInterrupt:
        logger.info("Sync tool stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())

"""
Configuration manager for Grocy-OurGroceries sync.
Handles loading and accessing configuration settings.
"""

import json
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self, config_path: str = 'config.json'):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file.
        
        Returns:
            The configuration as a dictionary
        """
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config from {self.config_path}: {e}")
            raise
    
    def get_grocy_config(self) -> Dict[str, Any]:
        """Get Grocy-specific configuration."""
        return self.config.get('grocy', {})
    
    def get_ourgroceries_config(self) -> Dict[str, Any]:
        """Get OurGroceries-specific configuration."""
        return self.config.get('ourgroceries', {})
    
    def get_sync_config(self) -> Dict[str, Any]:
        """Get sync-specific configuration."""
        return self.config.get('sync', {})
    
    def get_list_mappings(self) -> list:
        """Get list mappings configuration."""
        return self.get_sync_config().get('lists', [])
    
    def get_name_mappings(self) -> Dict[str, str]:
        """Get product name mappings."""
        return self.get_sync_config().get('name_mappings', {})
    
    def get_category_mappings(self) -> Dict[str, str]:
        """Get category name mappings."""
        return self.get_sync_config().get('category_mappings', {})
    
    def get_quantity_separator(self) -> str:
        """Get quantity separator."""
        return self.get_sync_config().get('quantity_separator', ' : ')
    
    def get_deletion_config(self) -> Dict[str, Any]:
        """Get deletion configuration."""
        return self.get_sync_config().get('deletion', {})
    
    def use_categories(self) -> bool:
        """Check if categories should be used."""
        return self.get_sync_config().get('use_categories', True)
    
    def get_sync_interval(self) -> int:
        """Get sync interval in minutes."""
        return self.get_sync_config().get('interval_minutes', 30)

"""
OurGroceries API Client
Handles communication with the OurGroceries API to manage shopping lists.
"""

import logging
import asyncio
import time
import traceback
from typing import Dict, List, Any, Optional, Union
from ourgroceries import OurGroceries

logger = logging.getLogger(__name__)

class OurGroceriesApiError(Exception):
    """Base exception for OurGroceries API errors."""
    pass

class OurGroceriesAuthenticationError(OurGroceriesApiError):
    """Exception raised when authentication to OurGroceries API fails."""
    pass

class OurGroceriesClient:
    def __init__(self, username: str, password: str, 
                 category_ids: Dict[str, str] = None, 
                 default_category_id: str = None, 
                 quantity_separator: str = " : ",
                 max_retries: int = 3,
                 retry_delay: int = 2):
        """
        Initialize the OurGroceries API client.
        
        Args:
            username: Your OurGroceries account email
            password: Your OurGroceries account password
            category_ids: Dictionary mapping category names to IDs
            default_category_id: Default category ID to use as fallback
            quantity_separator: Separator to use between item name and quantity
            max_retries: Maximum number of retries for failed operations
            retry_delay: Base delay between retries in seconds (will use exponential backoff)
        """
        self.username = username
        self.password = password
        self.client = OurGroceries(username, password)
        self.authenticated = False
        self.auth_time = 0
        self.auth_expiry = 3600  # Re-authenticate after 1 hour
        
        # Initialize category IDs with defaults if not provided
        self.category_ids = category_ids or {}
        
        # Set default category ID
        self.default_category_id = default_category_id or ""
        
        # Set quantity separator
        self.quantity_separator = quantity_separator
        
        # Retry settings
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Cache for frequently accessed data
        self._cache = {
            'lists': [],
            'list_items': {},
            'categories': {},
            'master_list': None,
            'last_added_item': None
        }
        
        # Cache expiry in seconds
        self._cache_expiry = {
            'lists': 300,  # 5 minutes
            'list_items': 60,  # 1 minute
            'categories': 60,  # 1 minute
            'master_list': 600  # 10 minutes
        }
        
        # Cache timestamps
        self._cache_time = {
            'lists': 0,
            'list_items': {},
            'categories': 0,
            'master_list': 0
        }
    
    async def _async_authenticate(self) -> bool:
        """
        Authenticate with OurGroceries asynchronously.
        
        Returns:
            True if authentication was successful, False otherwise
        """
        try:
            await self.client.login()
            self.authenticated = True
            self.auth_time = time.time()
            return True
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            self.authenticated = False
            raise OurGroceriesAuthenticationError(f"Failed to authenticate: {str(e)}")
    
    def authenticate(self) -> bool:
        """
        Authenticate with OurGroceries.
        
        Returns:
            True if authentication was successful, False otherwise
        """
        try:
            # Run the async login method in a synchronous context
            asyncio.run(self._async_authenticate())
            # Return the authentication status
            return self.authenticated
        except OurGroceriesAuthenticationError as e:
            logger.error(str(e))
            return False
        except Exception as e:
            logger.error(f"Unexpected error during authentication: {e}")
            return False
    
    def _ensure_authenticated(self) -> bool:
        """
        Ensure the client is authenticated, re-authenticating if necessary.
        
        Returns:
            True if authenticated, False otherwise
        """
        current_time = time.time()
        
        # Check if authentication has expired
        if self.authenticated and (current_time - self.auth_time) < self.auth_expiry:
            return True
            
        # Need to authenticate or re-authenticate
        return self.authenticate()
    
    def _run_with_retry(self, async_func, *args, **kwargs):
        """
        Run an async function with retry logic.
        
        Args:
            async_func: Async function to run
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            The result of the async function
            
        Raises:
            OurGroceriesApiError: If all retries fail
        """
        for attempt in range(self.max_retries + 1):
            try:
                # Ensure we're authenticated before each attempt
                if not self._ensure_authenticated():
                    raise OurGroceriesAuthenticationError("Failed to authenticate")
                
                # Run the async function
                return asyncio.run(async_func(*args, **kwargs))
            except Exception as e:
                # Last attempt failed
                if attempt >= self.max_retries:
                    logger.error(f"Operation failed after {self.max_retries + 1} attempts: {e}")
                    raise OurGroceriesApiError(f"Operation failed: {str(e)}")
                
                # Calculate delay with exponential backoff
                delay = self.retry_delay * (2 ** attempt)
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                time.sleep(delay)
                
                # Force re-authentication on next attempt
                self.authenticated = False
    
    def get_lists(self) -> List[Dict[str, Any]]:
        """
        Get all shopping lists with caching.
        
        Returns:
            A list of shopping lists
        """
        # Check if cache is valid
        current_time = time.time()
        if (current_time - self._cache_time['lists']) < self._cache_expiry['lists'] and self._cache['lists']:
            logger.debug("Using cached lists data")
            return self._cache['lists']
            
        try:
            # Run the async get_my_lists method with retry
            lists_data = self._run_with_retry(self.client.get_my_lists)
            
            # Convert to the expected format
            formatted_lists = []
            if isinstance(lists_data, list):
                for item in lists_data:
                    if isinstance(item, dict):
                        formatted_lists.append(item)
                    elif isinstance(item, str):
                        # If it's a string, create a dict with name and id
                        formatted_lists.append({'name': item, 'id': item})
            elif isinstance(lists_data, dict) and 'shoppingLists' in lists_data:
                formatted_lists = lists_data['shoppingLists']
            
            # Update cache
            self._cache['lists'] = formatted_lists
            self._cache_time['lists'] = current_time
            
            return formatted_lists
        except OurGroceriesApiError as e:
            logger.error(f"Failed to get lists: {e}")
            return []
    
    def get_list_by_name(self, list_name: str) -> Optional[Dict[str, Any]]:
        """
        Find a shopping list by name.
        
        Args:
            list_name: The name of the shopping list
            
        Returns:
            The shopping list data or None if not found
        """
        lists = self.get_lists()
        logger.debug(f"Looking for list '{list_name}' in {len(lists)} lists")
        
        for lst in lists:
            # Handle both string and dict formats
            if isinstance(lst, dict):
                list_name_from_dict = lst.get('name', '')
                if list_name_from_dict.lower() == list_name.lower():
                    return lst
            elif isinstance(lst, str):
                if lst.lower() == list_name.lower():
                    return {'name': lst, 'id': lst}
                    
        return None
    
    def get_list_items(self, list_id: str) -> List[Dict[str, Any]]:
        """
        Get all items in a specific shopping list with caching.
        
        Args:
            list_id: The ID of the shopping list
            
        Returns:
            A list of shopping list items
        """
        # Check if cache is valid
        current_time = time.time()
        cache_key = list_id
        if (cache_key in self._cache_time['list_items'] and 
            (current_time - self._cache_time['list_items'][cache_key]) < self._cache_expiry['list_items'] and
            cache_key in self._cache['list_items']):
            logger.debug(f"Using cached list items for list {list_id}")
            return self._cache['list_items'][cache_key]
            
        try:
            # Run the async get_list_items method with retry
            list_details = self._run_with_retry(self.client.get_list_items, list_id)
            
            # Handle different response formats
            items = []
            if isinstance(list_details, dict) and 'list' in list_details and 'items' in list_details['list']:
                items = list_details['list']['items']
            elif isinstance(list_details, list):
                items = list_details
            
            # Update cache
            self._cache['list_items'][cache_key] = items
            self._cache_time['list_items'][cache_key] = current_time
            
            return items
        except OurGroceriesApiError as e:
            logger.error(f"Failed to get list items: {e}")
            return []
    
    def add_item_to_list(self, list_id: str, item_name: str, quantity: str = None, category: str = None) -> bool:
        """
        Add an item to a shopping list.
        
        Args:
            list_id: The ID of the shopping list
            item_name: The name of the item to add
            quantity: Optional quantity string
            category: Optional category name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Format the item name with the quantity using the configured separator
            item_value = item_name
            if quantity:
                item_value = f"{item_name}{self.quantity_separator}{quantity}"
                
            # Get category ID if provided
            category_id = None
            if category:
                category_id = self.get_or_create_category(list_id, category)
                
            # Add item to list
            logger.info(f"Adding item '{item_value}' to list '{list_id}' with category id '{category_id}' ({category})")
            
            # Run the async add_item_to_list method with retry
            result = self._run_with_retry(
                self.client.add_item_to_list,
                list_id=list_id, 
                value=item_value, 
                category=category_id if category_id else None
            )
            
            # Invalidate cache for this list
            if list_id in self._cache['list_items']:
                del self._cache['list_items'][list_id]
                if list_id in self._cache_time['list_items']:
                    del self._cache_time['list_items'][list_id]
            
            # Try to extract the item ID from the response
            item_id = self._extract_item_id_from_response(result)
            if item_id:
                self._cache['last_added_item'] = {
                    'id': item_id,
                    'value': item_value,
                    'list_id': list_id
                }
            
            return True
        except OurGroceriesApiError as e:
            logger.error(f"Failed to add item to list: {e}")
            return False
    
    def _extract_item_id_from_response(self, response) -> Optional[str]:
        """
        Extract the item ID from an add_item_to_list response.
        
        Args:
            response: The response from add_item_to_list
            
        Returns:
            The item ID or None if not found
        """
        try:
            if isinstance(response, dict) and 'itemId' in response:
                return response['itemId']
        except Exception:
            pass
        return None
    
    def remove_item_from_list(self, list_id: str, item_id: str) -> bool:
        """
        Remove an item from a shopping list.
        
        Args:
            list_id: The ID of the shopping list
            item_id: The ID of the item to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.debug(f"Removing item with ID '{item_id}' from list '{list_id}'")
            
            # Run the async remove_item_from_list method with retry
            self._run_with_retry(self.client.remove_item_from_list, list_id, item_id)
            
            # Invalidate cache for this list
            if list_id in self._cache['list_items']:
                del self._cache['list_items'][list_id]
                if list_id in self._cache_time['list_items']:
                    del self._cache_time['list_items'][list_id]
            
            return True
        except OurGroceriesApiError as e:
            logger.error(f"Failed to remove item from list: {e}")
            return False
    
    def get_master_list(self) -> Dict[str, Any]:
        """
        Get the master list with caching.
        
        Returns:
            The master list data
        """
        # Check if cache is valid
        current_time = time.time()
        if ((current_time - self._cache_time['master_list']) < self._cache_expiry['master_list'] and 
            self._cache['master_list'] is not None):
            logger.debug("Using cached master list data")
            return self._cache['master_list']
            
        try:
            # Run the async get_master_list method with retry
            master_list = self._run_with_retry(self.client.get_master_list)
            
            # Update cache
            self._cache['master_list'] = master_list
            self._cache_time['master_list'] = current_time
            
            return master_list
        except OurGroceriesApiError as e:
            logger.error(f"Failed to get master list: {e}")
            return {}
        
    def get_categories(self) -> List[Dict[str, Any]]:
        """
        Get all categories with caching.

        Returns:
            A list of categories
        """
        # Check if cache is valid
        current_time = time.time()
        if (current_time - self._cache_time['categories']) < self._cache_expiry['categories'] and self._cache['categories']:
            logger.debug("Using cached categories data")
            return self._cache['categories']

        try:
            # Run the async get_categories method with retry
            categories_data = self._run_with_retry(self.client.get_category_items)
            # logger.info(f"Categories data: {categories_data}")
            # Convert to the expected format
            formatted_categories = []
            cat_items = categories_data.get('list',{}).get('items',[])
            logger.info(f"Categories items: {cat_items}")
            if isinstance(cat_items, list):
                for item in cat_items:
                    if isinstance(item, dict):
                        formatted_categories.append(item)
                    elif isinstance(item, str):
                        # If it's a string, create a dict with name and id
                        formatted_categories.append({'name': item, 'id': item})
            elif isinstance(categories_data, dict) and 'categories' in categories_data:
                formatted_categories = categories_data['categories']

            # Update cache
            self._cache['categories'] = formatted_categories
            self._cache_time['categories'] = current_time
            logger.info(f"Formatted category items: {formatted_categories}")

            return formatted_categories
        except OurGroceriesApiError as e:
            logger.error(f"Failed to get categories: {e}")
            return []
    
    def find_category_in_categories(self, category_name: str) -> Optional[str]:
        """
        Find a category by name in the categories list.

        Args:
            category_name: The name of the category

        Returns:
            The category ID or None if not found
        """
        categories = self.get_categories()
        logger.info(f"Looking for category '{category_name}' in {len(categories)} categories")

        for category in categories:
            # Handle both string and dict formats
            if isinstance(category, dict):
                category_name_from_dict = category.get('name', '')
                if category_name_from_dict.lower() == category_name.lower():
                    logger.info(f"Found category ID for '{category_name}': {category.get('id')}")
                    return category.get('id')

        return None
    
    def find_category_in_category_mappings(self, category_name):
        # Let's try to use the configured category IDs
        category_name_lower = category_name.lower()
        
        logger.info(f"Category Mappings: {self.category_ids.items()}")
        
        # # First, try direct match
        if category_name_lower in self.category_ids:
            category_id = self.category_ids[category_name_lower]
            logger.info(f"Using exact match category ID for '{category_name}': {category_id}")
            return category_id
        
        # Try to find a partial match
        for key, category_id in self.category_ids.items():
            if key in category_name_lower or category_name_lower in key:
                logger.info(f"Using partial match category ID for '{category_name}': {category_id}")
                return category_id
            
        return None
    
    def get_or_create_category(self, list_id: str, category_name: str) -> Optional[str]:
        """
        Get a category ID by name, or create it if it doesn't exist.
        
        Args:
            list_id: The ID of the shopping list
            category_name: The name of the category
            
        Returns:
            The category ID or None if failed
        """
        try:
            category = self.find_category_in_categories(category_name)
            
            if not category: 
                # If we get here, we need to try a different approach
                category = self.find_category_in_category_mappings(category_name)
            
            if not category: 
                # If we still can't find a match, try to create the category
                logger.debug(f"Creating new category: {category_name}")
                

                # Run the async create_category method with retry
                self._run_with_retry(self.client.create_category, category_name)
                logger.debug(f"Category creation request sent for '{category_name}'")
                
                # Invalidate master list cache
                self._cache['master_list'] = None
                self._cache['categories'] = None

                category = self.find_category_in_categories(category_name)
            
            return category
            
        except Exception as e:
            logger.error(f"Failed to get or create category: {e}")
            
            # As a last resort, return the default category ID if available
            if self.default_category_id:
                logger.debug(f"Using fallback category ID: {self.default_category_id}")
                return self.default_category_id
            else:
                logger.warning(f"No default category ID configured")
                return None
    
    def get_last_added_item_id(self) -> Optional[str]:
        """
        Get the ID of the last added item.
        
        Returns:
            The ID of the last added item, or None if not available
        """
        if self._cache['last_added_item'] and 'id' in self._cache['last_added_item']:
            return self._cache['last_added_item']['id']
        return None
    
    def test_connection(self) -> bool:
        """
        Test the connection to the OurGroceries API.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Attempt to authenticate and get lists
            if self._ensure_authenticated() and self.get_lists():
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to connect to OurGroceries API: {e}")
            return False
    
    def clear_cache(self, cache_type: str = None):
        """
        Clear the client cache.
        
        Args:
            cache_type: Type of cache to clear (lists, list_items, master_list)
                       If None, clears all caches
        """
        if cache_type is None:
            self._cache['lists'] = []
            self._cache['list_items'] = {}
            self._cache['master_list'] = None
            self._cache_time['lists'] = 0
            self._cache_time['list_items'] = {}
            self._cache_time['master_list'] = 0
            logger.debug("Cleared all caches")
        elif cache_type == 'lists':
            self._cache['lists'] = []
            self._cache_time['lists'] = 0
            logger.debug("Cleared lists cache")
        elif cache_type == 'list_items':
            self._cache['list_items'] = {}
            self._cache_time['list_items'] = {}
            logger.debug("Cleared list_items cache")
        elif cache_type == 'master_list':
            self._cache['master_list'] = None
            self._cache_time['master_list'] = 0
            logger.debug("Cleared master_list cache")
        else:
            logger.warning(f"Unknown cache type: {cache_type}")

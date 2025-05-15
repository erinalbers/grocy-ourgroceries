"""
Grocy API Client
Handles communication with the Grocy API to manage shopping lists and products.
"""

import requests
import json
import logging
import time
from typing import Dict, List, Any, Optional, Union
from requests.exceptions import RequestException, ConnectionError, Timeout, HTTPError

logger = logging.getLogger(__name__)

class GrocyApiError(Exception):
    """Base exception for Grocy API errors."""
    pass

class GrocyConnectionError(GrocyApiError):
    """Exception raised when connection to Grocy API fails."""
    pass

class GrocyAuthenticationError(GrocyApiError):
    """Exception raised when authentication to Grocy API fails."""
    pass

class GrocyClient:
    def __init__(self, api_url: str, api_key: str, timeout: int = 10, max_retries: int = 3):
        """
        Initialize the Grocy API client.
        
        Args:
            api_url: The URL to the Grocy API (e.g., https://your-grocy-instance/api/)
            api_key: Your Grocy API key
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.headers = {
            'GROCY-API-KEY': api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        # Cache for frequently accessed data
        self._cache = {
            'quantity_units': {},
            'product_groups': {},
            'products': {}
        }
        
    def _make_request(self, method: str, endpoint: str, params: Dict = None, 
                     data: Dict = None, retry_count: int = 0) -> requests.Response:
        """
        Make a request to the Grocy API with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: URL parameters
            data: Request body data
            retry_count: Current retry attempt
            
        Returns:
            Response object
            
        Raises:
            GrocyConnectionError: If connection fails after all retries
            GrocyAuthenticationError: If authentication fails
            GrocyApiError: For other API errors
        """
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=data,
                timeout=self.timeout
            )
            
            # Log request details at debug level
            logger.debug(f"API Request: {method} {url}")
            if params:
                logger.debug(f"Params: {params}")
            
            # Check for authentication errors first
            if response.status_code == 401:
                raise GrocyAuthenticationError(f"Authentication failed: {response.status_code} {response.reason}")
                
            # Handle other HTTP errors
            try:
                response.raise_for_status()
            except HTTPError as e:
                if response.status_code == 401:
                    raise GrocyAuthenticationError(f"Authentication failed: {str(e)}")
                elif response.status_code >= 500:
                    # Server errors might be temporary, retry if possible
                    if retry_count < self.max_retries:
                        wait_time = 2 ** retry_count  # Exponential backoff
                        logger.warning(f"Server error {response.status_code}, retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        return self._make_request(method, endpoint, params, data, retry_count + 1)
                    else:
                        raise GrocyApiError(f"Server error after {self.max_retries} retries: {str(e)}")
                else:
                    # Client errors are not retried
                    raise GrocyApiError(f"API error: {response.status_code} - {response.text}")
            
            return response
            
        except GrocyAuthenticationError:
            # Re-raise authentication errors
            raise
        except (ConnectionError, Timeout) as e:
            # Network errors might be temporary, retry if possible
            if retry_count < self.max_retries:
                wait_time = 2 ** retry_count  # Exponential backoff
                logger.warning(f"Connection error, retrying in {wait_time}s: {str(e)}")
                time.sleep(wait_time)
                return self._make_request(method, endpoint, params, data, retry_count + 1)
            else:
                raise GrocyConnectionError(f"Connection failed after {self.max_retries} retries: {str(e)}")
        except Exception as e:
            # Catch-all for unexpected errors
            raise GrocyApiError(f"Unexpected error: {str(e)}")
    
    def test_connection(self) -> bool:
        """
        Test the connection to the Grocy API.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            self._make_request("GET", "/system/info")
            return True
        except GrocyApiError as e:
            logger.error(f"Failed to connect to Grocy API: {e}")
            return False
    
    def get_shopping_lists(self) -> List[Dict[str, Any]]:
        """
        Get all shopping lists from Grocy.
        
        Returns:
            A list of shopping lists
        """
        try:
            response = self._make_request("GET", "/objects/shopping_lists")
            return response.json()
        except GrocyApiError as e:
            logger.error(f"Failed to get shopping lists: {e}")
            return []
    
    def get_shopping_list_items(self, list_id: int) -> List[Dict[str, Any]]:
        """
        Get all items in a specific shopping list.
        
        Args:
            list_id: The ID of the shopping list
            
        Returns:
            A list of shopping list items with product details
        """
        try:
            response = self._make_request(
                "GET", 
                "/objects/shopping_list",
                params={"query[]": f"shopping_list_id={list_id}"}
            )
            
            items = response.json()
            logger.debug(f"Found {len(items)} items in shopping list {list_id}")
            
            # Get product details for each item
            for item in items:
                if 'product_id' in item and item['product_id']:
                    product = self.get_product(item['product_id'])
                    if product:
                        item['product_details'] = product
            
            return items
        except GrocyApiError as e:
            logger.error(f"Failed to get shopping list items for list {list_id}: {e}")
            return []
    
    def get_product(self, product_id: int) -> Dict[str, Any]:
        """
        Get product details by ID with caching.
        
        Args:
            product_id: The ID of the product
            
        Returns:
            Product details or empty dict if not found
        """
        # Check cache first
        if product_id in self._cache['products']:
            logger.debug(f"Using cached product data for ID {product_id}")
            return self._cache['products'][product_id]
        
        try:
            response = self._make_request("GET", f"/objects/products/{product_id}")
            product_data = response.json()
            
            # Ensure we have a dictionary to work with
            if isinstance(product_data, list) and len(product_data) > 0:
                product = product_data[0]  # Take the first item if it's a list
            elif isinstance(product_data, dict):
                product = product_data
            else:
                logger.warning(f"Unexpected product data format for ID {product_id}: {type(product_data)}")
                return {}
            
            # Get product category if available
            if 'product_group_id' in product and product['product_group_id']:
                category = self.get_product_group(product['product_group_id'])
                if category:
                    product['category'] = category
            
            # Get quantity units
            if 'qu_id_purchase' in product and product['qu_id_purchase']:
                purchase_unit = self.get_quantity_unit(product['qu_id_purchase'])
                if purchase_unit:
                    product['purchase_unit'] = purchase_unit
            
            if 'qu_id_stock' in product and product['qu_id_stock']:
                stock_unit = self.get_quantity_unit(product['qu_id_stock'])
                if stock_unit:
                    product['stock_unit'] = stock_unit
            
            # Get quantity unit conversions
            conversions = self.get_quantity_unit_conversions(product_id)
            if conversions:
                product['quantity_unit_conversions'] = conversions
            
            # Cache the result
            self._cache['products'][product_id] = product
            return product
        except GrocyApiError as e:
            logger.error(f"Failed to get product {product_id}: {e}")
            return {}
    
    def get_product_group(self, group_id: int) -> Dict[str, Any]:
        """
        Get product group (category) details by ID with caching.
        
        Args:
            group_id: The ID of the product group
            
        Returns:
            Product group details or empty dict if not found
        """
        # Check cache first
        if group_id in self._cache['product_groups']:
            return self._cache['product_groups'][group_id]
        
        try:
            response = self._make_request("GET", f"/objects/product_groups/{group_id}")
            group = response.json()
            
            # Cache the result
            self._cache['product_groups'][group_id] = group
            return group
        except GrocyApiError as e:
            logger.error(f"Failed to get product group {group_id}: {e}")
            return {}
    
    def get_quantity_unit(self, qu_id: int) -> Dict[str, Any]:
        """
        Get quantity unit details by ID with caching.
        
        Args:
            qu_id: The ID of the quantity unit
            
        Returns:
            Quantity unit details or empty dict if not found
        """
        # Check cache first
        if qu_id in self._cache['quantity_units']:
            return self._cache['quantity_units'][qu_id]
        
        try:
            response = self._make_request("GET", f"/objects/quantity_units/{qu_id}")
            unit = response.json()
            
            # Cache the result
            self._cache['quantity_units'][qu_id] = unit
            return unit
        except GrocyApiError as e:
            logger.error(f"Failed to get quantity unit {qu_id}: {e}")
            return {}
    
    def get_quantity_unit_conversions(self, product_id: int) -> List[Dict[str, Any]]:
        """
        Get quantity unit conversions for a product.
        
        Args:
            product_id: The ID of the product
            
        Returns:
            List of quantity unit conversions
        """
        try:
            response = self._make_request(
                "GET", 
                "/objects/quantity_unit_conversions",
                params={"query[]": f"product_id={product_id}"}
            )
            return response.json()
        except GrocyApiError as e:
            logger.error(f"Failed to get quantity unit conversions for product {product_id}: {e}")
            return []
    
    def clear_cache(self, cache_type: str = None):
        """
        Clear the client cache.
        
        Args:
            cache_type: Type of cache to clear (products, product_groups, quantity_units)
                       If None, clears all caches
        """
        if cache_type is None:
            for cache in self._cache:
                self._cache[cache] = {}
            logger.debug("Cleared all caches")
        elif cache_type in self._cache:
            self._cache[cache_type] = {}
            logger.debug(f"Cleared {cache_type} cache")
        else:
            logger.warning(f"Unknown cache type: {cache_type}")

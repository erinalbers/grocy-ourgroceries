"""
Tests for the Grocy API client.
"""

import pytest
import json
from unittest.mock import MagicMock, patch
import requests
from requests.exceptions import ConnectionError, Timeout, HTTPError

from clients.grocy_client import GrocyClient, GrocyApiError, GrocyConnectionError, GrocyAuthenticationError

# Test constants
API_URL = "https://grocy.example.com/api"
API_KEY = "test-api-key"

class TestGrocyClient:
    """Test suite for the GrocyClient class."""
    
    def test_init(self):
        """Test client initialization."""
        client = GrocyClient(API_URL, API_KEY)
        
        assert client.api_url == API_URL
        assert client.api_key == API_KEY
        assert client.headers["GROCY-API-KEY"] == API_KEY
        assert client.headers["Content-Type"] == "application/json"
        assert client.timeout == 10  # Default timeout
        assert client.max_retries == 3  # Default max retries
    
    def test_test_connection_success(self, mock_requests, mock_grocy_responses):
        """Test successful connection test."""
        mock_request, mock_response = mock_requests
        mock_response.json.return_value = mock_grocy_responses["system_info"]
        
        client = GrocyClient(API_URL, API_KEY)
        result = client.test_connection()
        
        assert result is True
        mock_request.assert_called_once_with(
            method="GET",
            url=f"{API_URL}/system/info",
            headers=client.headers,
            params=None,
            json=None,
            timeout=10
        )
    
    def test_test_connection_failure(self, mock_requests):
        """Test failed connection test."""
        mock_request, mock_response = mock_requests
        mock_request.side_effect = ConnectionError("Connection refused")
        
        client = GrocyClient(API_URL, API_KEY)
        result = client.test_connection()
        
        assert result is False
    
    def test_get_shopping_lists(self, mock_requests, mock_grocy_responses):
        """Test getting shopping lists."""
        mock_request, mock_response = mock_requests
        mock_response.json.return_value = mock_grocy_responses["shopping_lists"]
        
        client = GrocyClient(API_URL, API_KEY)
        result = client.get_shopping_lists()
        
        assert result == mock_grocy_responses["shopping_lists"]
        mock_request.assert_called_once_with(
            method="GET",
            url=f"{API_URL}/objects/shopping_lists",
            headers=client.headers,
            params=None,
            json=None,
            timeout=10
        )
    
    def test_get_shopping_list_items(self, mock_requests, mock_grocy_responses):
        """Test getting shopping list items."""
        mock_request, mock_response = mock_requests
        
        # Set up multiple responses for sequential calls - add enough responses for all calls
        responses = []
        # First item
        responses.append(mock_grocy_responses["shopping_list_items"])  # Shopping list items
        
        # For each item in the shopping list, we need product details
        for _ in range(len(mock_grocy_responses["shopping_list_items"])):
            responses.append(mock_grocy_responses["product"])              # Product details
            responses.append(mock_grocy_responses["product_group"])        # Product group
            responses.append(mock_grocy_responses["quantity_unit"])        # Stock quantity unit
            responses.append(mock_grocy_responses["quantity_unit"])        # Purchase quantity unit
            responses.append(mock_grocy_responses["quantity_unit_conversions"])  # Conversions
        
        mock_response.json.side_effect = responses
        
        client = GrocyClient(API_URL, API_KEY)
        result = client.get_shopping_list_items(1)
        
        # Check that the result contains the shopping list items
        assert len(result) == len(mock_grocy_responses["shopping_list_items"])
        
        # Check that the first API call was to get shopping list items
        assert mock_request.call_args_list[0][1]["url"] == f"{API_URL}/objects/shopping_list"
        assert mock_request.call_args_list[0][1]["params"] == {"query[]": "shopping_list_id=1"}
    
    def test_get_product(self, mock_requests, mock_grocy_responses):
        """Test getting product details."""
        mock_request, mock_response = mock_requests
        
        # Set up multiple responses for sequential calls
        responses = [
            mock_grocy_responses["product"],              # Product details
            mock_grocy_responses["product_group"],        # Product group
            mock_grocy_responses["quantity_unit"],        # Stock quantity unit
            mock_grocy_responses["quantity_unit"],        # Purchase quantity unit
            mock_grocy_responses["quantity_unit_conversions"]  # Conversions
        ]
        mock_response.json.side_effect = responses
        
        client = GrocyClient(API_URL, API_KEY)
        result = client.get_product(201)
        
        # Check that the result contains the product details
        assert result["id"] == mock_grocy_responses["product"]["id"]
        assert result["name"] == mock_grocy_responses["product"]["name"]
        
        # Check that the product has category and quantity unit information
        assert "category" in result
        assert "stock_unit" in result
        assert "purchase_unit" in result
        assert "quantity_unit_conversions" in result
        
        # Check that the first API call was to get product details
        assert mock_request.call_args_list[0][1]["url"] == f"{API_URL}/objects/products/201"
    
    def test_get_product_group(self, mock_requests, mock_grocy_responses):
        """Test getting product group details."""
        mock_request, mock_response = mock_requests
        mock_response.json.return_value = mock_grocy_responses["product_group"]
        
        client = GrocyClient(API_URL, API_KEY)
        result = client.get_product_group(5)
        
        assert result == mock_grocy_responses["product_group"]
        mock_request.assert_called_once_with(
            method="GET",
            url=f"{API_URL}/objects/product_groups/5",
            headers=client.headers,
            params=None,
            json=None,
            timeout=10
        )
    
    def test_get_quantity_unit(self, mock_requests, mock_grocy_responses):
        """Test getting quantity unit details."""
        mock_request, mock_response = mock_requests
        mock_response.json.return_value = mock_grocy_responses["quantity_unit"]
        
        client = GrocyClient(API_URL, API_KEY)
        result = client.get_quantity_unit(8)
        
        assert result == mock_grocy_responses["quantity_unit"]
        mock_request.assert_called_once_with(
            method="GET",
            url=f"{API_URL}/objects/quantity_units/8",
            headers=client.headers,
            params=None,
            json=None,
            timeout=10
        )
    
    def test_get_quantity_unit_conversions(self, mock_requests, mock_grocy_responses):
        """Test getting quantity unit conversions."""
        mock_request, mock_response = mock_requests
        mock_response.json.return_value = mock_grocy_responses["quantity_unit_conversions"]
        
        client = GrocyClient(API_URL, API_KEY)
        result = client.get_quantity_unit_conversions(201)
        
        assert result == mock_grocy_responses["quantity_unit_conversions"]
        mock_request.assert_called_once_with(
            method="GET",
            url=f"{API_URL}/objects/quantity_unit_conversions",
            headers=client.headers,
            params={"query[]": "product_id=201"},
            json=None,
            timeout=10
        )
    
    def test_make_request_retry_on_connection_error(self, mock_requests):
        """Test that _make_request retries on connection error."""
        mock_request, mock_response = mock_requests
        
        # First call raises ConnectionError, second call succeeds
        mock_request.side_effect = [
            ConnectionError("Connection refused"),
            mock_response
        ]
        mock_response.json.return_value = {"success": True}
        
        client = GrocyClient(API_URL, API_KEY)
        with patch('time.sleep') as mock_sleep:  # Mock sleep to avoid waiting
            result = client._make_request("GET", "/test")
        
        assert result == mock_response
        assert mock_request.call_count == 2
        mock_sleep.assert_called_once()  # Should sleep once between retries
    
    def test_make_request_retry_on_timeout(self, mock_requests):
        """Test that _make_request retries on timeout."""
        mock_request, mock_response = mock_requests
        
        # First call raises Timeout, second call succeeds
        mock_request.side_effect = [
            Timeout("Request timed out"),
            mock_response
        ]
        mock_response.json.return_value = {"success": True}
        
        client = GrocyClient(API_URL, API_KEY)
        with patch('time.sleep') as mock_sleep:  # Mock sleep to avoid waiting
            result = client._make_request("GET", "/test")
        
        assert result == mock_response
        assert mock_request.call_count == 2
        mock_sleep.assert_called_once()  # Should sleep once between retries
    
    def test_make_request_retry_on_server_error(self, mock_requests):
        """Test that _make_request retries on server error."""
        mock_request, mock_response = mock_requests
        
        # Create a response that will raise HTTPError with status code 500
        error_response = MagicMock()
        error_response.raise_for_status.side_effect = HTTPError("500 Server Error")
        error_response.status_code = 500
        
        # First call returns error response, second call succeeds
        mock_request.side_effect = [error_response, mock_response]
        
        client = GrocyClient(API_URL, API_KEY)
        with patch('time.sleep') as mock_sleep:  # Mock sleep to avoid waiting
            result = client._make_request("GET", "/test")
        
        assert result == mock_response
        assert mock_request.call_count == 2
        mock_sleep.assert_called_once()  # Should sleep once between retries
    
    def test_make_request_max_retries_exceeded(self, mock_requests):
        """Test that _make_request raises exception after max retries."""
        mock_request, mock_response = mock_requests
        
        # All calls raise ConnectionError
        mock_request.side_effect = ConnectionError("Connection refused")
        
        client = GrocyClient(API_URL, API_KEY, max_retries=2)
        with patch('time.sleep') as mock_sleep:  # Mock sleep to avoid waiting
            with pytest.raises(GrocyConnectionError):
                client._make_request("GET", "/test")
        
        assert mock_request.call_count == 3  # Initial call + 2 retries
        assert mock_sleep.call_count == 2  # Should sleep twice between retries
    
    def test_make_request_authentication_error(self):
        """Test that _make_request raises GrocyAuthenticationError on 401."""
        # Create a direct patch for requests.request
        with patch('requests.request') as mock_request:
            # Create a response that will raise HTTPError with status code 401
            error_response = MagicMock()
            error_response.raise_for_status.side_effect = HTTPError("401 Unauthorized")
            error_response.status_code = 401
            error_response.text = "Unauthorized"
            
            mock_request.return_value = error_response
            
            client = GrocyClient(API_URL, API_KEY)
            with pytest.raises(GrocyAuthenticationError):
                client._make_request("GET", "/test")
    
    def test_make_request_client_error(self):
        """Test that _make_request raises GrocyApiError on client error."""
        # Create a direct patch for requests.request
        with patch('requests.request') as mock_request:
            # Create a response that will raise HTTPError with status code 400
            error_response = MagicMock()
            error_response.raise_for_status.side_effect = HTTPError("400 Bad Request")
            error_response.status_code = 400
            error_response.text = "Bad Request"
            
            mock_request.return_value = error_response
            
            client = GrocyClient(API_URL, API_KEY)
            with pytest.raises(GrocyApiError):
                client._make_request("GET", "/test")
    
    def test_clear_cache(self):
        """Test clearing the cache."""
        client = GrocyClient(API_URL, API_KEY)
        
        # Add some items to the cache
        client._cache['products'][201] = {"id": "201", "name": "Water"}
        client._cache['product_groups'][5] = {"id": "5", "name": "Beverages"}
        client._cache['quantity_units'][8] = {"id": "8", "name": "Bottle"}
        
        # Clear specific cache
        client.clear_cache('products')
        assert client._cache['products'] == {}
        assert client._cache['product_groups'] == {5: {"id": "5", "name": "Beverages"}}
        assert client._cache['quantity_units'] == {8: {"id": "8", "name": "Bottle"}}
        
        # Clear all caches
        client.clear_cache()
        assert client._cache['products'] == {}
        assert client._cache['product_groups'] == {}
        assert client._cache['quantity_units'] == {}

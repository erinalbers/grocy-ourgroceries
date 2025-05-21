"""
Tests for the OurGroceries API client.
"""

import pytest
import json
import time
from unittest.mock import MagicMock, patch, call

from clients.ourgroceries_client import OurGroceriesClient, OurGroceriesApiError, OurGroceriesAuthenticationError

# Test constants
USERNAME = "test@example.com"
PASSWORD = "test-password"
CATEGORY_IDS = {
    "beverages": "cat1",
    "dairy": "cat2"
}
DEFAULT_CATEGORY_ID = "cat1"

class TestOurGroceriesClient:
    """Test suite for the OurGroceriesClient class."""
    
    def test_init(self):
        """Test client initialization."""
        with patch('clients.ourgroceries_client.OurGroceries') as mock_og:
            mock_client = MagicMock()
            mock_og.return_value = mock_client
            
            client = OurGroceriesClient(USERNAME, PASSWORD, CATEGORY_IDS, DEFAULT_CATEGORY_ID)
            
            assert client.username == USERNAME
            assert client.password == PASSWORD
            assert client.category_ids == CATEGORY_IDS
            assert client.default_category_id == DEFAULT_CATEGORY_ID
            assert client.authenticated is False
            assert client.quantity_separator == " : "  # Default separator
            assert client.max_retries == 3  # Default max retries
            
            # Check that OurGroceries client was initialized
            mock_og.assert_called_once_with(USERNAME, PASSWORD)
    
    def test_authenticate_success(self):
        """Test successful authentication."""
        with patch('clients.ourgroceries_client.OurGroceries') as mock_og:
            mock_client = MagicMock()
            mock_og.return_value = mock_client
            
            # Create a patched version of asyncio.run that sets authenticated to True
            with patch('asyncio.run') as mock_run:
                # Configure mock_run to actually call our mock_async_auth function
                def side_effect(coro):
                    # This will execute the coroutine and return its result
                    import asyncio
                    loop = asyncio.new_event_loop()
                    try:
                        return loop.run_until_complete(coro)
                    finally:
                        loop.close()
                
                mock_run.side_effect = side_effect
                
                # Create a client with a mocked _async_authenticate method
                client = OurGroceriesClient(USERNAME, PASSWORD)
                
                # Replace the _async_authenticate method with a mock that sets authenticated
                original_method = client._async_authenticate
                
                async def mock_async_auth():
                    client.authenticated = True
                    client.auth_time = time.time()
                    return True
                    
                client._async_authenticate = mock_async_auth
                
                # Now call authenticate
                result = client.authenticate()
                
                # Restore the original method
                client._async_authenticate = original_method
                
                assert result is True
                assert client.authenticated is True
    
    def test_authenticate_failure(self):
        """Test failed authentication."""
        with patch('clients.ourgroceries_client.OurGroceries') as mock_og:
            mock_client = MagicMock()
            mock_og.return_value = mock_client
            
            # Patch the _async_authenticate method to raise exception
            with patch('clients.ourgroceries_client.OurGroceriesClient._async_authenticate') as mock_async_auth:
                mock_async_auth.side_effect = Exception("Authentication failed")
                
                client = OurGroceriesClient(USERNAME, PASSWORD)
                result = client.authenticate()
                
                assert result is False
                assert client.authenticated is False
                mock_async_auth.assert_called_once()
    
    def test_ensure_authenticated_already_authenticated(self):
        """Test _ensure_authenticated when already authenticated."""
        with patch('clients.ourgroceries_client.OurGroceries') as mock_og:
            mock_client = MagicMock()
            mock_og.return_value = mock_client
            
            client = OurGroceriesClient(USERNAME, PASSWORD)
            client.authenticated = True
            client.auth_time = time.time()  # Set auth time to now
            
            with patch.object(client, 'authenticate') as mock_authenticate:
                result = client._ensure_authenticated()
            
            assert result is True
            mock_authenticate.assert_not_called()  # authenticate should not be called
    
    def test_ensure_authenticated_expired(self):
        """Test _ensure_authenticated when authentication has expired."""
        with patch('clients.ourgroceries_client.OurGroceries') as mock_og:
            mock_client = MagicMock()
            mock_og.return_value = mock_client
            
            client = OurGroceriesClient(USERNAME, PASSWORD)
            client.authenticated = True
            client.auth_time = time.time() - 4000  # Set auth time to more than an hour ago
            
            with patch.object(client, 'authenticate') as mock_authenticate:
                mock_authenticate.return_value = True
                result = client._ensure_authenticated()
            
            assert result is True
            mock_authenticate.assert_called_once()  # authenticate should be called
    
    def test_ensure_authenticated_not_authenticated(self):
        """Test _ensure_authenticated when not authenticated."""
        with patch('clients.ourgroceries_client.OurGroceries') as mock_og:
            mock_client = MagicMock()
            mock_og.return_value = mock_client
            
            client = OurGroceriesClient(USERNAME, PASSWORD)
            client.authenticated = False
            
            with patch.object(client, 'authenticate') as mock_authenticate:
                mock_authenticate.return_value = True
                result = client._ensure_authenticated()
            
            assert result is True
            mock_authenticate.assert_called_once()  # authenticate should be called
    
    def test_run_with_retry_success_first_try(self):
        """Test _run_with_retry succeeding on first try."""
        with patch('clients.ourgroceries_client.OurGroceries') as mock_og:
            mock_client = MagicMock()
            mock_og.return_value = mock_client
            
            client = OurGroceriesClient(USERNAME, PASSWORD)
            client.authenticated = True
            client.auth_time = time.time()
            
            # Set up mock for _ensure_authenticated
            with patch.object(client, '_ensure_authenticated') as mock_ensure_auth:
                mock_ensure_auth.return_value = True
                
                # Set up mock for asyncio.run
                with patch('asyncio.run') as mock_run:
                    mock_run.return_value = {"success": True}
                    
                    # Create a mock async function
                    mock_async_func = MagicMock()
                    
                    result = client._run_with_retry(mock_async_func, "arg1", kwarg1="value1")
                    
                    assert result == {"success": True}
                    mock_run.assert_called_once_with(mock_async_func("arg1", kwarg1="value1"))
    
    def test_run_with_retry_success_after_retry(self):
        """Test _run_with_retry succeeding after a retry."""
        with patch('clients.ourgroceries_client.OurGroceries') as mock_og:
            mock_client = MagicMock()
            mock_og.return_value = mock_client
            
            client = OurGroceriesClient(USERNAME, PASSWORD)
            client.authenticated = True
            client.auth_time = time.time()
            client.retry_delay = 0  # Set retry delay to 0 for testing
            
            # Set up mock for _ensure_authenticated
            with patch.object(client, '_ensure_authenticated') as mock_ensure_auth:
                mock_ensure_auth.return_value = True
                
                # Set up mock for asyncio.run
                with patch('asyncio.run') as mock_run:
                    # First call raises exception, second call succeeds
                    mock_run.side_effect = [Exception("First attempt failed"), {"success": True}]
                    
                    # Create a mock async function
                    mock_async_func = MagicMock()
                    
                    # Mock sleep to avoid waiting
                    with patch('time.sleep'):
                        result = client._run_with_retry(mock_async_func, "arg1", kwarg1="value1")
                    
                    assert result == {"success": True}
                    assert mock_run.call_count == 2
    
    def test_run_with_retry_all_attempts_fail(self):
        """Test _run_with_retry when all attempts fail."""
        with patch('clients.ourgroceries_client.OurGroceries') as mock_og:
            mock_client = MagicMock()
            mock_og.return_value = mock_client
            
            client = OurGroceriesClient(USERNAME, PASSWORD)
            client.authenticated = True
            client.auth_time = time.time()
            client.max_retries = 2
            client.retry_delay = 0  # Set retry delay to 0 for testing
            
            # Set up mock for _ensure_authenticated
            with patch.object(client, '_ensure_authenticated') as mock_ensure_auth:
                mock_ensure_auth.return_value = True
                
                # Set up mock for asyncio.run
                with patch('asyncio.run') as mock_run:
                    # All calls raise exception
                    mock_run.side_effect = Exception("All attempts failed")
                    
                    # Create a mock async function
                    mock_async_func = MagicMock()
                    
                    # Mock sleep to avoid waiting
                    with patch('time.sleep'):
                        with pytest.raises(OurGroceriesApiError):
                            client._run_with_retry(mock_async_func, "arg1", kwarg1="value1")
                    
                    assert mock_run.call_count == 3  # Initial attempt + 2 retries
    
    def test_get_lists_from_cache(self):
        """Test get_lists using cached data."""
        with patch('clients.ourgroceries_client.OurGroceries') as mock_og:
            mock_client = MagicMock()
            mock_og.return_value = mock_client
            
            client = OurGroceriesClient(USERNAME, PASSWORD)
            client.authenticated = True
            client.auth_time = time.time()
            
            # Set up cache
            client._cache['lists'] = [{"id": "list1", "name": "Shopping List"}]
            client._cache_time['lists'] = time.time()
            
            result = client.get_lists()
            
            assert result == [{"id": "list1", "name": "Shopping List"}]
            mock_client.get_my_lists.assert_not_called()  # Should use cache, not call API
    
    def test_get_lists_from_api(self, mock_ourgroceries_responses):
        """Test get_lists fetching from API."""
        with patch('clients.ourgroceries_client.OurGroceries') as mock_og:
            mock_client = MagicMock()
            mock_og.return_value = mock_client
            
            client = OurGroceriesClient(USERNAME, PASSWORD)
            client.authenticated = True
            client.auth_time = time.time()
            
            # Ensure cache is expired
            client._cache_time['lists'] = 0
            
            # Set up mock for _run_with_retry
            with patch.object(client, '_run_with_retry') as mock_run_with_retry:
                mock_run_with_retry.return_value = mock_ourgroceries_responses["lists"]
                
                result = client.get_lists()
                
                assert len(result) == 3
                assert result[0]["name"] == "Shopping List"
                mock_run_with_retry.assert_called_once_with(mock_client.get_my_lists)
    
    def test_get_list_by_name_found(self):
        """Test get_list_by_name when list is found."""
        with patch('clients.ourgroceries_client.OurGroceries') as mock_og:
            mock_client = MagicMock()
            mock_og.return_value = mock_client
            
            client = OurGroceriesClient(USERNAME, PASSWORD)
            
            # Mock get_lists to return test data
            with patch.object(client, 'get_lists') as mock_get_lists:
                mock_get_lists.return_value = [
                    {"id": "list1", "name": "Shopping List"},
                    {"id": "list2", "name": "Pet Supplies"}
                ]
                
                result = client.get_list_by_name("Shopping List")
            
            assert result == {"id": "list1", "name": "Shopping List"}
    
    def test_get_list_by_name_not_found(self):
        """Test get_list_by_name when list is not found."""
        with patch('clients.ourgroceries_client.OurGroceries') as mock_og:
            mock_client = MagicMock()
            mock_og.return_value = mock_client
            
            client = OurGroceriesClient(USERNAME, PASSWORD)
            
            # Mock get_lists to return test data
            with patch.object(client, 'get_lists') as mock_get_lists:
                mock_get_lists.return_value = [
                    {"id": "list1", "name": "Shopping List"},
                    {"id": "list2", "name": "Pet Supplies"}
                ]
                
                result = client.get_list_by_name("Non-existent List")
            
            assert result is None
    
    def test_get_list_items_from_cache(self):
        """Test get_list_items using cached data."""
        with patch('clients.ourgroceries_client.OurGroceries') as mock_og:
            mock_client = MagicMock()
            mock_og.return_value = mock_client
            
            client = OurGroceriesClient(USERNAME, PASSWORD)
            client.authenticated = True
            client.auth_time = time.time()
            
            # Set up cache
            list_id = "list1"
            client._cache['list_items'][list_id] = [{"id": "item1", "value": "Water"}]
            client._cache_time['list_items'][list_id] = time.time()
            
            result = client.get_list_items(list_id)
            
            assert result == [{"id": "item1", "value": "Water"}]
            mock_client.get_list_items.assert_not_called()  # Should use cache, not call API
    
    def test_get_list_items_from_api(self, mock_ourgroceries_responses):
        """Test get_list_items fetching from API."""
        with patch('clients.ourgroceries_client.OurGroceries') as mock_og:
            mock_client = MagicMock()
            mock_og.return_value = mock_client
            
            client = OurGroceriesClient(USERNAME, PASSWORD)
            client.authenticated = True
            client.auth_time = time.time()
            
            # Ensure cache is expired
            list_id = "list1"
            if list_id in client._cache_time['list_items']:
                client._cache_time['list_items'][list_id] = 0
            
            # Set up mock for _run_with_retry
            with patch.object(client, '_run_with_retry') as mock_run_with_retry:
                mock_run_with_retry.return_value = mock_ourgroceries_responses["list_items"]
                
                result = client.get_list_items(list_id)
                
                assert len(result) == 2
                assert result[0]["value"] == "Water : 3 Bottles"
                mock_run_with_retry.assert_called_once_with(mock_client.get_list_items, list_id)
    
    def test_add_item_to_list(self, mock_ourgroceries_responses):
        """Test add_item_to_list."""
        with patch('clients.ourgroceries_client.OurGroceries') as mock_og:
            mock_client = MagicMock()
            mock_og.return_value = mock_client
            
            client = OurGroceriesClient(USERNAME, PASSWORD)
            client.authenticated = True
            client.auth_time = time.time()
            
            # Mock get_or_create_category
            with patch.object(client, 'get_or_create_category') as mock_get_category:
                mock_get_category.return_value = "cat1"
                
                # Set up mock for _run_with_retry
                with patch.object(client, '_run_with_retry') as mock_run_with_retry:
                    mock_run_with_retry.return_value = mock_ourgroceries_responses["add_item"]
                    
                    result = client.add_item_to_list("list1", "Water", "3 Bottles", "Beverages")
                
                assert result is True
                mock_get_category.assert_called_once_with("list1", "Beverages")
                mock_run_with_retry.assert_called_once_with(
                    mock_client.add_item_to_list,
                    list_id="list1",
                    value="Water : 3 Bottles",
                    category="cat1"
                )
                
                # Check that cache was invalidated
                assert "list1" not in client._cache['list_items']
                
                # Check that last added item was stored
                assert client._cache['last_added_item']['id'] == "item3"
                assert client._cache['last_added_item']['value'] == "Water : 3 Bottles"
                assert client._cache['last_added_item']['list_id'] == "list1"
    
    def test_remove_item_from_list(self):
        """Test remove_item_from_list."""
        with patch('clients.ourgroceries_client.OurGroceries') as mock_og:
            mock_client = MagicMock()
            mock_og.return_value = mock_client
            
            client = OurGroceriesClient(USERNAME, PASSWORD)
            client.authenticated = True
            client.auth_time = time.time()
            
            # Set up cache to verify it gets invalidated
            list_id = "list1"
            client._cache['list_items'][list_id] = [{"id": "item1", "value": "Water"}]
            client._cache_time['list_items'][list_id] = time.time()
            
            # Set up mock for _run_with_retry
            with patch.object(client, '_run_with_retry') as mock_run_with_retry:
                mock_run_with_retry.return_value = None  # remove_item_from_list doesn't return anything
                
                result = client.remove_item_from_list(list_id, "item1")
                
                assert result is True
                mock_run_with_retry.assert_called_once_with(mock_client.remove_item_from_list, list_id, "item1")
                
                # Check that cache was invalidated
                assert list_id not in client._cache['list_items']
    
    def test_get_master_list_from_cache(self):
        """Test get_master_list using cached data."""
        with patch('clients.ourgroceries_client.OurGroceries') as mock_og:
            mock_client = MagicMock()
            mock_og.return_value = mock_client
            
            client = OurGroceriesClient(USERNAME, PASSWORD)
            client.authenticated = True
            client.auth_time = time.time()
            
            # Set up cache
            client._cache['master_list'] = {"list": {"items": [{"id": "cat1", "value": "Beverages"}]}}
            client._cache_time['master_list'] = time.time()
            
            result = client.get_master_list()
            
            assert result == {"list": {"items": [{"id": "cat1", "value": "Beverages"}]}}
            mock_client.get_master_list.assert_not_called()  # Should use cache, not call API
    
    def test_get_master_list_from_api(self, mock_ourgroceries_responses):
        """Test get_master_list fetching from API."""
        with patch('clients.ourgroceries_client.OurGroceries') as mock_og:
            mock_client = MagicMock()
            mock_og.return_value = mock_client
            
            client = OurGroceriesClient(USERNAME, PASSWORD)
            client.authenticated = True
            client.auth_time = time.time()
            
            # Ensure cache is expired
            client._cache_time['master_list'] = 0
            
            # Set up mock for _run_with_retry
            with patch.object(client, '_run_with_retry') as mock_run_with_retry:
                mock_run_with_retry.return_value = mock_ourgroceries_responses["master_list"]
                
                result = client.get_master_list()
                
                assert result == mock_ourgroceries_responses["master_list"]
                mock_run_with_retry.assert_called_once_with(mock_client.get_master_list)
    
    def test_get_or_create_category_found_in_category_list(self):
        """Test get_or_create_category when category is found in master list."""
        with patch('clients.ourgroceries_client.OurGroceries') as mock_og:
            mock_client = MagicMock()
            mock_og.return_value = mock_client
            
            client = OurGroceriesClient(USERNAME, PASSWORD)
            
            # Mock get_master_list to return test data
            with patch.object(client, 'get_categories') as mock_get_categories:
                mock_get_categories.return_value = {'list': 
                    {
                        'notes': '', 'name': '', 'id': 'Yo9ElScZec8WxayJHqR8XR', 'listType': 'CATEGORY', 'externalListAccess': 'NONE', 'versionId': 'f4xQnb7fcR5U6st3D1GRAn', 
                        'items': [
                            {'name': 'Beverages', 'value': 'Beverages', 'id': 'roYHsiYY3ry0Dir6m4upyh', 'sortOrder': ';d'}, 
                            {'name': 'Refrigerated Goods', 'value': 'Refrigerated Goods', 'id': 'zAapgj4PAK56ixQXHyyZTu', 'sortOrder': 'g8'}, 
                            {'name': 'Baked Goods', 'value': 'Baked Goods', 'id': 'lHptIF4vB5lOvu2fY9qazu', 'sortOrder': 'm2'}, 
                            {'name': 'Snacks', 'value': 'Snacks', 'id': 'g7OwjklWQuQpQxe0UQ9SZH', 'sortOrder': ';<X'}, 
                            {'name': 'Household', 'value': 'Household', 'id': '9bl83gDWksvax1tHY2ia83', 'sortOrder': ';PD'}, 
                            {'name': 'Meat', 'value': 'Meat', 'id': 'zGo0TOBVTJ9NlkAfCSVtI6', 'sortOrder': 'SL'}, 
                            {'name': 'Frozen Foods', 'value': 'Frozen Foods', 'id': 'geoeGJNZU6z3eheHbbPehF', 'sortOrder': 'c<'}, 
                            {'name': 'Canned Goods', 'value': 'Canned Goods', 'id': 'RSZei0QMw27SVI2eIqTeCj', 'sortOrder': '6i'}, 
                            {'name': 'Dry Goods', 'value': 'Dry Goods', 'id': 'Oye0VOYJ0VA5Op1CpWLDXA', 'sortOrder': ':U@'}, 
                            {'name': 'Pet Supplies', 'value': 'Pet Supplies', 'id': '4GmqmiFehtIQgjFkDuakMC', 'sortOrder': ';Z:'}, 
                            {'name': 'Condiments', 'value': 'Condiments', 'id': 'hW34b9TAbI7nfZjByBcHly', 'sortOrder': '87`'}, 
                            {'name': 'Spices', 'value': 'Spices', 'id': 'oGCz0kkEjImj6V05B1CZeb', 'sortOrder': '9FP'},
                            {'name': 'Sweets', 'value': 'Sweets', 'id': 'FTP7LGwuecofpLeWXEruHt'}, 
                            {'name': 'Baking and Cooking', 'value': 'Baking and Cooking', 'id': 'Bsk4oJ7UmH23DzZJwN5zbx'}, 
                            {'name': 'Pets', 'value': 'Pets', 'id': 'N6hqNvG2EpyJJgh0bM0fQK'}, 
                            {'name': 'Produce', 'value': 'Produce', 'id': 'M3qgIOMh53Iirb26grPAUJ', 'sortOrder': '3l'}, 
                            {'name': 'Meats', 'value': 'Meats', 'id': 'C8nPqMvVtT9yMEHney44QU'}
                        ]}, 'command': 'getList'}
                
                result = client.get_or_create_category("list1", "Beverages")
            
            assert result == "roYHsiYY3ry0Dir6m4upyh"
    
    def test_get_or_create_category_found_in_category_ids(self):
        """Test get_or_create_category when category is found in category_ids."""
        with patch('clients.ourgroceries_client.OurGroceries') as mock_og:
            mock_client = MagicMock()
            mock_og.return_value = mock_client
            
            client = OurGroceriesClient(USERNAME, PASSWORD, CATEGORY_IDS, DEFAULT_CATEGORY_ID)
            
            # Mock get_master_list to return empty data
            with patch.object(client, 'get_master_list') as mock_get_master_list:
                mock_get_master_list.return_value = {"list": {"items": []}}
                
                result = client.get_or_create_category("list1", "beverages")
            
            assert result == "cat1"  # Should match the category ID from CATEGORY_IDS
    
    def test_get_or_create_category_partial_match(self):
        """Test get_or_create_category with partial match in category_ids."""
        with patch('clients.ourgroceries_client.OurGroceries') as mock_og:
            mock_client = MagicMock()
            mock_og.return_value = mock_client
            
            client = OurGroceriesClient(USERNAME, PASSWORD, CATEGORY_IDS, DEFAULT_CATEGORY_ID)
            
            # Mock get_master_list to return empty data
            with patch.object(client, 'get_master_list') as mock_get_master_list:
                mock_get_master_list.return_value = {"list": {"items": []}}
                
                result = client.get_or_create_category("list1", "Cold Beverages")
            
            assert result == "cat1"  # Should match "beverages" in CATEGORY_IDS
    
    def test_get_or_create_category_create_new(self):
        """Test get_or_create_category creating a new category."""
        with patch('clients.ourgroceries_client.OurGroceries') as mock_og:
            mock_client = MagicMock()
            mock_og.return_value = mock_client
            
            client = OurGroceriesClient(USERNAME, PASSWORD, CATEGORY_IDS, DEFAULT_CATEGORY_ID)
            client.authenticated = True
            client.auth_time = time.time()
            
            # Mock get_master_list to return empty data
            with patch.object(client, 'get_master_list') as mock_get_master_list:
                mock_get_master_list.return_value = {"list": {"items": []}}
                
                # Set up mock for _run_with_retry
                with patch.object(client, '_run_with_retry') as mock_run_with_retry:
                    mock_run_with_retry.return_value = None  # create_category doesn't return anything
                    
                    result = client.get_or_create_category("list1", "New Category")
                
                assert result == DEFAULT_CATEGORY_ID  # Should use default category ID
                mock_run_with_retry.assert_called_once_with(mock_client.create_category, "New Category")
    
    def test_get_last_added_item_id(self):
        """Test get_last_added_item_id."""
        with patch('clients.ourgroceries_client.OurGroceries') as mock_og:
            mock_client = MagicMock()
            mock_og.return_value = mock_client
            
            client = OurGroceriesClient(USERNAME, PASSWORD)
            
            # No last added item
            assert client.get_last_added_item_id() is None
            
            # Set last added item
            client._cache['last_added_item'] = {
                'id': 'item3',
                'value': 'Water : 3 Bottles',
                'list_id': 'list1'
            }
            
            assert client.get_last_added_item_id() == 'item3'
    
    def test_test_connection_success(self):
        """Test successful connection test."""
        with patch('clients.ourgroceries_client.OurGroceries') as mock_og:
            mock_client = MagicMock()
            mock_og.return_value = mock_client
            
            client = OurGroceriesClient(USERNAME, PASSWORD)
            
            # Mock _ensure_authenticated and get_lists
            with patch.object(client, '_ensure_authenticated') as mock_ensure_auth:
                mock_ensure_auth.return_value = True
                
                with patch.object(client, 'get_lists') as mock_get_lists:
                    mock_get_lists.return_value = [{"id": "list1", "name": "Shopping List"}]
                    
                    result = client.test_connection()
            
            assert result is True
            mock_ensure_auth.assert_called_once()
            mock_get_lists.assert_called_once()
    
    def test_test_connection_failure(self):
        """Test failed connection test."""
        with patch('clients.ourgroceries_client.OurGroceries') as mock_og:
            mock_client = MagicMock()
            mock_og.return_value = mock_client
            
            client = OurGroceriesClient(USERNAME, PASSWORD)
            
            # Mock _ensure_authenticated to fail
            with patch.object(client, '_ensure_authenticated') as mock_ensure_auth:
                mock_ensure_auth.return_value = False
                
                result = client.test_connection()
            
            assert result is False
            mock_ensure_auth.assert_called_once()
    
    def test_clear_cache(self):
        """Test clearing the cache."""
        with patch('clients.ourgroceries_client.OurGroceries') as mock_og:
            mock_client = MagicMock()
            mock_og.return_value = mock_client
            
            client = OurGroceriesClient(USERNAME, PASSWORD)
            
            # Set up cache
            client._cache['lists'] = [{"id": "list1", "name": "Shopping List"}]
            client._cache_time['lists'] = time.time()
            
            client._cache['list_items']["list1"] = [{"id": "item1", "value": "Water"}]
            client._cache_time['list_items']["list1"] = time.time()
            
            client._cache['master_list'] = {"list": {"items": []}}
            client._cache_time['master_list'] = time.time()
            
            # Clear specific cache
            client.clear_cache('lists')
            assert client._cache['lists'] == []
            assert client._cache_time['lists'] == 0
            assert "list1" in client._cache['list_items']
            assert client._cache['master_list'] is not None
            
            # Clear all caches
            client.clear_cache()
            assert client._cache['lists'] == []
            assert client._cache['list_items'] == {}
            assert client._cache['master_list'] is None
            assert client._cache_time['lists'] == 0
            assert client._cache_time['list_items'] == {}
            assert client._cache_time['master_list'] == 0

"""
Pytest configuration and fixtures for the Grocy-OurGroceries sync tool tests.
"""

import pytest
import json
import os
from unittest.mock import MagicMock, patch

# Define paths relative to the tests directory
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'test_data')

# Create test data directory if it doesn't exist
os.makedirs(TEST_DATA_DIR, exist_ok=True)

# Mock response data
GROCY_SYSTEM_INFO = {
    "grocy_version": "3.3.0",
    "php_version": "7.4.3",
    "sqlite_version": "3.31.1"
}

GROCY_SHOPPING_LISTS = [
    {"id": "1", "name": "Shopping List"},
    {"id": "2", "name": "Pet Supplies"},
    {"id": "3", "name": "Costco"}
]

GROCY_SHOPPING_LIST_ITEMS = [
    {
        "id": "101",
        "shopping_list_id": "1",
        "product_id": "201",
        "note": None,
        "amount": 3,
        "qu_id": "8",
        "done": 0
    },
    {
        "id": "102",
        "shopping_list_id": "1",
        "product_id": "202",
        "note": None,
        "amount": 1,
        "qu_id": "5",
        "done": 0
    }
]

GROCY_PRODUCT = {
    "id": "201",
    "name": "Water",
    "description": "Bottled water",
    "product_group_id": "5",
    "qu_id_stock": "8",
    "qu_id_purchase": "8"
}

GROCY_PRODUCT_GROUP = {
    "id": "5",
    "name": "Beverages"
}

GROCY_QUANTITY_UNIT = {
    "id": "8",
    "name": "Bottle",
    "name_plural": "Bottles"
}

GROCY_QUANTITY_UNIT_CONVERSIONS = [
    {
        "id": "15",
        "from_qu_id": "8",
        "to_qu_id": "3",
        "factor": "1",
        "product_id": "201"
    }
]

OURGROCERIES_LISTS = {
    "shoppingLists": [
        {
            "id": "list1",
            "name": "Shopping List",
            "activeCount": 5
        },
        {
            "id": "list2",
            "name": "Pet Supplies",
            "activeCount": 2
        },
        {
            "id": "list3",
            "name": "Costco",
            "activeCount": 3
        }
    ]
}

OURGROCERIES_LIST_ITEMS = {
    "list": {
        "id": "list1",
        "name": "Shopping List",
        "items": [
            {
                "id": "item1",
                "value": "Water : 3 Bottles",
                "crossedOff": False,
                "categoryId": "cat1"
            },
            {
                "id": "item2",
                "value": "Milk",
                "crossedOff": False,
                "categoryId": "cat2"
            }
        ]
    }
}

OURGROCERIES_MASTER_LIST = {
    "list": {
        "id": "master",
        "name": "Master",
        "items": [
            {
                "id": "cat1",
                "value": "Beverages",
                "categoryId": None
            },
            {
                "id": "cat2",
                "value": "Dairy",
                "categoryId": None
            }
        ]
    }
}

OURGROCERIES_ADD_ITEM_RESPONSE = {
    "itemId": "item3"
}

@pytest.fixture
def mock_grocy_responses():
    """Fixture to provide mock responses for Grocy API calls."""
    return {
        "system_info": GROCY_SYSTEM_INFO,
        "shopping_lists": GROCY_SHOPPING_LISTS,
        "shopping_list_items": GROCY_SHOPPING_LIST_ITEMS,
        "product": GROCY_PRODUCT,
        "product_group": GROCY_PRODUCT_GROUP,
        "quantity_unit": GROCY_QUANTITY_UNIT,
        "quantity_unit_conversions": GROCY_QUANTITY_UNIT_CONVERSIONS
    }

@pytest.fixture
def mock_ourgroceries_responses():
    """Fixture to provide mock responses for OurGroceries API calls."""
    return {
        "lists": OURGROCERIES_LISTS,
        "list_items": OURGROCERIES_LIST_ITEMS,
        "master_list": OURGROCERIES_MASTER_LIST,
        "add_item": OURGROCERIES_ADD_ITEM_RESPONSE
    }

@pytest.fixture
def mock_requests():
    """Fixture to mock the requests library."""
    with patch('requests.request') as mock_request:
        # Create a mock response
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock()
        
        # Set up the mock request to return our mock response
        mock_request.return_value = mock_response
        
        yield mock_request, mock_response

@pytest.fixture
def mock_asyncio():
    """Fixture to mock asyncio.run."""
    with patch('asyncio.run') as mock_run:
        yield mock_run

@pytest.fixture
def mock_ourgroceries():
    """Fixture to mock the OurGroceries client."""
    with patch('clients.ourgroceries_client.OurGroceries') as mock_og:
        mock_client = MagicMock()
        mock_og.return_value = mock_client
        
        # Mock the async methods
        mock_client.login = MagicMock()
        mock_client.get_my_lists = MagicMock()
        mock_client.get_list_items = MagicMock()
        mock_client.add_item_to_list = MagicMock()
        mock_client.remove_item_from_list = MagicMock()
        mock_client.get_master_list = MagicMock()
        mock_client.create_category = MagicMock()
        
        yield mock_og, mock_client

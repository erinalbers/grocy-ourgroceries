# Grocy to OurGroceries Sync

This tool synchronizes shopping lists from Grocy to OurGroceries, allowing you to manage your grocery planning in Grocy while using the OurGroceries app for in-store shopping.

## Features

- One-way synchronization from Grocy to OurGroceries
- Configurable sync interval
- Support for multiple shopping lists
- Mapping between Grocy product names and OurGroceries item names
- Support for product categories with category mapping
- Smart handling of quantity units (singular/plural forms)

## Project Versions

This repository contains two versions of the sync tool:

- **v1**: The original version with a monolithic class structure
- **v2**: A refactored version with improved code organization and modularity

## Requirements

- Python 3.8+
- Grocy instance with API access
- OurGroceries account

## Setup

1. Clone this repository
2. Copy `config.example.json` to `config.json` and edit with your credentials

### Running with Python

```bash
# Installing
pip3 install -r requirements.txt

# Run once and exit
python3 main.py --config config.json --once

# Run continuously with scheduled syncs
python3 main.py --config config.json

# Enable debug logging
python3 main.py --config config.json --debug
```

### Running with Docker

```bash
# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down

# Executing a manual sync from the host
docker exec grocy-ourgroceries-sync python main.py --once 
```

## Configuration

Edit `config.json` with your Grocy API key and OurGroceries credentials:

```json
{
  "grocy": {
    "api_url": "https://your-grocy-instance/api/",
    "api_key": "your-api-key"
  },
  "ourgroceries": {
    "username": "your-email@example.com",
    "password": "your-password"
  },
  "sync": {
    "interval_minutes": 30,
    "lists": [
      {
        "grocy_list_id": 1,
        "ourgroceries_list_name": "Groceries"
      }
    ],
    "name_mappings": {
      "Grocy Product Name": "OurGroceries Item Name"
    },
    "category_mappings": {
      "Grocy Category Name": "OurGroceries Category Name"
    }
  }
}
```

You do not have to Map products or categories, but you can if you have the need. I started with mapping, but realized there weren't many great reasons to not just delete everything and let my Grocy configurations take over. YMMV.

### Contributing

Contributions are welcome! Please feel free to submit a Pull Request or make a feature request, or you can also drop "appreciation" at http://buymeacoffee.com/erinalbers if you want your contribution to be more... inspirational.

## License

MIT

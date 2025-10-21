import requests
import logging
from typing import Optional

# Get a logger instance for this module
logger = logging.getLogger(__name__)

ADDRESS_API_URL = "https://kommisdd.dresden.de/net4/public/ogcapi/collections/L134/items?limit=100000"

def get_address_id(address: str) -> int:
    """
    Fetches the address ID for a given address string from the Dresden OGC API.

    Args:
        address: The address to search for (e.g., "Chemnitzer Straße 42").

    Returns:
        The ID of the address.

    Raises:
        ValueError: If no exact match is found for the address.
        requests.exceptions.RequestException: If there is an error fetching the data.
    """
    try:
        response = requests.get(ADDRESS_API_URL)
        response.raise_for_status()
        data = response.json()

        for feature in data.get("features", []):
            properties = feature.get("properties", {})
            if properties.get("adresse", "").lower() == address.lower():
                address_id = properties.get("id")
                logger.info(f"Found address ID {address_id} for address '{address}'")
                return address_id

        logger.warning(f"No exact match found for address: {address}")
        raise ValueError(f"Address not found: {address}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching address data: {e}")
        raise

import json
import logging
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ADDRESS_API_URL = "https://kommisdd.dresden.de/net4/public/ogcapi/collections/L134/items?limit=100000"
OPTIMIZED_CACHE_FILE = "address_lookup.json"

def build_optimized_cache():
    """
    Downloads the full address dataset and creates a small, optimized
    address-to-ID lookup file.
    """
    logging.info(f"Attempting to download data from: {ADDRESS_API_URL}")
    try:
        response = requests.get(ADDRESS_API_URL, timeout=60) # Longer timeout for large file
        response.raise_for_status()
        data = response.json()
        logging.info("Successfully downloaded and parsed address data.")

        features = data.get("features", [])
        if not features:
            logging.error("No 'features' found in the downloaded data.")
            return

        address_lookup = {}
        for feature in features:
            props = feature.get("properties", {})
            address = props.get("adresse")
            feature_id = feature.get("id")
            if address and feature_id is not None:
                # Use the lowercase, stripped address as the key for consistency
                address_lookup[address.lower().strip()] = feature_id

        if not address_lookup:
            logging.error("Could not extract any address-ID pairs.")
            return

        logging.info(f"Extracted {len(address_lookup)} address-ID pairs.")

        with open(OPTIMIZED_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(address_lookup, f, indent=2)

        logging.info(f"Successfully created optimized cache file: {OPTIMIZED_CACHE_FILE}")

    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to download address data: {e}")
    except json.JSONDecodeError:
        logging.error("Failed to parse JSON from the API response.")
    except IOError as e:
        logging.error(f"Failed to write to cache file: {e}")


if __name__ == "__main__":
    build_optimized_cache()

# Automated Firewall Dynamic Update Audit Script using PAN-OS SDK

import logging
import os
from datetime import datetime
from panos.panorama import Panorama
from panos.firewall import Firewall
from panos.device import DeviceGroup
from panos.errors import PanDeviceError

# Logging configuration
def setup_logger(name):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    return logging.getLogger(name)

logger = setup_logger("panos_sdk_audit")

# Function to get environment variables
def get_env_variable(var_name):
    value = os.getenv(var_name)
    if value is None:
        logger.error(f"Environment variable '{var_name}' not set.")
    return value

# Fetch Panorama credentials from environment
PANORAMA_IP = get_env_variable("PANORAMA_IP")
PANORAMA_USERNAME = get_env_variable("PANORAMA_USERNAME")
PANORAMA_PASSWORD = get_env_variable("PANORAMA_PASSWORD")

# Connect to Panorama
try:
    panorama = Panorama(PANORAMA_IP, PANORAMA_USERNAME, PANORAMA_PASSWORD)
    logger.info("Successfully connected to Panorama.")
except PanDeviceError as e:
    logger.error(f"Error connecting to Panorama: {e}")
    exit(1)

# Function to fetch all firewalls from Panorama
def get_firewalls():
    try:
        devices = panorama.refresh_devices()
        firewalls = [fw for fw in devices if isinstance(fw, Firewall)]
        logger.info(f"Found {len(firewalls)} firewalls.")
        return firewalls
    except PanDeviceError as e:
        logger.error(f"Error fetching firewalls: {e}")
        return []

# Function to check dynamic update versions
def check_dynamic_updates(firewall):
    try:
        info = firewall.refresh_system_info()
        updates = {
            "App/Threat": info.app_version,
            "Antivirus": info.av_version,
            "Wildfire": info.wildfire_version,
            "URL Filtering": info.url_filtering_version,
            "PAN-OS": info.sw_version
        }
        logger.info(f"Firewall {firewall.serial} updates: {updates}")
        return updates
    except PanDeviceError as e:
        logger.error(f"Error checking updates for firewall {firewall.serial}: {e}")
        return {}

# Main function to perform update audit
def audit_updates():
    logger.info("Starting Firewall Dynamic Update Audit with PAN-OS SDK")
    firewalls = get_firewalls()
    if not firewalls:
        logger.error("No firewalls found. Exiting.")
        return

    for firewall in firewalls:
        updates = check_dynamic_updates(firewall)
        for update_type, version in updates.items():
            if version == "Unknown":
                logger.warning(f"Unable to determine {update_type} version on firewall {firewall.serial}.")
            else:
                logger.info(f"{update_type} version on {firewall.serial}: {version}")

if __name__ == "__main__":
    audit_updates()

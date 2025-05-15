import os
import requests
import logging
from xml.etree import ElementTree as ET

# Setup logging
LOG_FILE = 'check_dynamic_updates.log'
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load env variables
PANORAMA_IP = os.getenv('PANORAMA_IP')
PANORAMA_USERNAME = os.getenv('PANORAMA_USERNAME')
PANORAMA_PASSWORD = os.getenv('PANORAMA_PASSWORD')

BASE_URL = f"https://{PANORAMA_IP}/api"

# Suppress warnings
requests.packages.urllib3.disable_warnings()

def get_api_key():
    logging.info("Authenticating to Panorama...")
    try:
        params = {
            'type': 'keygen',
            'user': PANORAMA_USERNAME,
            'password': PANORAMA_PASSWORD
        }
        response = requests.get(BASE_URL, params=params, verify=False)
        response.raise_for_status()
        return ET.fromstring(response.text).find('.//key').text
    except Exception as e:
        logging.error(f"Failed to get API key: {e}")
        return None

def api_call(cmd, api_key, target=None):
    try:
        params = {
            'type': 'op',
            'cmd': cmd,
            'key': api_key
        }
        if target:
            params['target'] = target
        response = requests.get(BASE_URL, params=params, verify=False)
        response.raise_for_status()
        return ET.fromstring(response.text)
    except Exception as e:
        logging.error(f"API call failed: {e}")
        return None

def get_firewalls(api_key):
    logging.info("Fetching list of connected firewalls...")
    cmd = "<show><devices><connected></connected></devices></show>"
    tree = api_call(cmd, api_key)
    if not tree:
        return []
    return [entry.findtext('serial') for entry in tree.findall('.//entry')]

def get_current_versions(api_key, serial):
    versions = {}

    logging.info(f"Fetching current versions for {serial}...")

    # PAN-OS
    system_info = api_call("<show><system><info/></system></show>", api_key, target=serial)
    versions['panos'] = system_info.findtext('.//sw-version', default="N/A") if system_info else "N/A"

    # Antivirus
    av_info = api_call("<request><anti-virus><upgrade><info></info></upgrade></anti-virus></request>", api_key, target=serial)
    versions['antivirus'] = av_info.findtext('.//current-version', default="N/A") if av_info else "N/A"

    # Wildfire
    wf_info = api_call("<request><wildfire><upgrade><info></info></upgrade></wildfire></request>", api_key, target=serial)
    versions['wildfire'] = wf_info.findtext('.//current-version', default="N/A") if wf_info else "N/A"

    # App/Threat (Content)
    content_info = api_call("<request><content><upgrade><info></info></upgrade></content></request>", api_key, target=serial)
    versions['app_threat'] = content_info.findtext('.//current-version', default="N/A") if content_info else "N/A"

    # URL Filtering (manual check or assume N/A)
    versions['url_filtering'] = "Manual"

    return versions

def get_latest_versions(api_key):
    logging.info("Fetching latest available dynamic update versions...")

    def get_latest(cmd):
        tree = api_call(cmd, api_key)
        return tree.findtext('.//latest-version', default="N/A") if tree else "N/A"

    return {
        'antivirus': get_latest("<request><anti-virus><upgrade><check></check></upgrade></anti-virus></request>"),
        'wildfire': get_latest("<request><wildfire><upgrade><check></check></upgrade></wildfire></request>"),
        'app_threat': get_latest("<request><content><upgrade><check></check></upgrade></content></request>"),
        'url_filtering': "Manual"
    }

def compare_versions(current, latest):
    result = {}
    for key in latest:
        cur = current.get(key, "N/A")
        lat = latest.get(key, "N/A")
        result[key] = {
            "current": cur,
            "latest": lat,
            "status": "✅ Up to date" if cur == lat else "❌ Outdated"
        }
    return result

def main():
    print("\n📋 Dynamic Update Status Check\n")
    logging.info("Script started.")

    api_key = get_api_key()
    if not api_key:
        print("❌ Failed to authenticate.")
        return

    firewalls = get_firewalls(api_key)
    if not firewalls:
        print("❌ No firewalls found.")
        return

    latest_versions = get_latest_versions(api_key)

    for serial in firewalls:
        print(f"\n🔍 Firewall: {serial}")
        current = get_current_versions(api_key, serial)
        results = compare_versions(current, latest_versions)

        print(f"  PAN-OS Version     : {current['panos']}")
        for update_type, detail in results.items():
            print(f"  {update_type.title():<18}: {detail['current']} vs {detail['latest']} => {detail['status']}")
        logging.info(f"{serial} versions: {results}")

    logging.info("Script completed.\n")


if __name__ == "__main__":
    main()

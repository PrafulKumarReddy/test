import os
import requests
import logging
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET

# Setup logging
LOG_FILE = 'check_license_status.log'
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Auth settings
PANORAMA_IP = os.getenv('PANORAMA_IP')
PANORAMA_USERNAME = os.getenv('PANORAMA_USERNAME')
PANORAMA_PASSWORD = os.getenv('PANORAMA_PASSWORD')

BASE_URL = f"https://{PANORAMA_IP}/api"
requests.packages.urllib3.disable_warnings()

def get_api_key():
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
        logging.error(f"API Key generation failed: {e}")
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
    cmd = "<show><devices><connected></connected></devices></show>"
    tree = api_call(cmd, api_key)
    if tree is None:
        return []
    return [s for s in (entry.findtext('serial') for entry in tree.findall('.//entry')) if s is not None]

def get_license_status(api_key, serial):
    licenses = {}
    tree = api_call("<request><license><info></info></license></request>", api_key, target=serial)
    if tree is None:
        return licenses

    for entry in tree.findall('.//entry'):
        feature = entry.findtext('feature', 'Unknown')
        description = entry.findtext('description', '')
        expire_date = entry.findtext('expires', '')
        licenses[feature.lower()] = {
            'description': description,
            'expires': expire_date
        }

    return licenses

def analyze_license_status(license_data):
    today = datetime.today()
    cutoff = today + timedelta(days=180)

    result = {}
    features = ['app threat', 'antivirus', 'wildfire', 'url filtering']

    for feature in features:
        lic = license_data.get(feature)
        if not lic:
            result[feature] = "❌ Not Installed"
            continue
        exp = lic.get('expires', 'N/A')
        try:
            exp_date = datetime.strptime(exp, '%Y/%m/%d')
            if exp_date < today:
                result[feature] = f"❌ Expired on {exp}"
            elif exp_date <= cutoff:
                result[feature] = f"⚠️ Expiring on {exp}"
            else:
                result[feature] = f"✅ Valid until {exp}"
        except:
            result[feature] = f"⚠️ Unknown Expiry: {exp}"

    return result

def main():
    print("\n📋 License Status Check\n")
    logging.info("License check started.")
    api_key = get_api_key()
    if not api_key:
        print("❌ Panorama API authentication failed.")
        return

    firewalls = get_firewalls(api_key)
    if not firewalls:
        print("❌ No firewalls found.")
        return

    for serial in firewalls:
        print(f"\nFirewall: {serial}")
        license_data = get_license_status(api_key, serial)
        analysis = analyze_license_status(license_data)

        for feature, status in analysis.items():
            print(f"  {feature.title():<15}: {status}")
        logging.info(f"{serial} license check: {analysis}")

    logging.info("License check completed.")

if __name__ == "__main__":
    main()

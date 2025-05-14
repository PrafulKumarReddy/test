import os
import requests
import xml.etree.ElementTree as ET

# --- Load credentials from environment ---
PANORAMA_IP = os.getenv("PANORAMA_IP")
USERNAME = os.getenv("PANORAMA_USERNAME")
PASSWORD = os.getenv("PANORAMA_PASSWORD")

if not all([PANORAMA_IP, USERNAME, PASSWORD]):
    print("Missing required environment variables: PANORAMA_IP, PANORAMA_USERNAME, PANORAMA_PASSWORD")
    exit(1)

# --- Function to fetch API key ---
def get_api_key():
    try:
        url = f"https://{PANORAMA_IP}/api/"
        params = {
            "type": "keygen",
            "user": USERNAME,
            "password": PASSWORD
        }
        response = requests.get(url, params=params, verify=False, timeout=10)
        root = ET.fromstring(response.text)
        return root.findtext(".//key")
    except Exception as e:
        print(f"Error getting API key: {e}")
        exit(1)

# --- Function to fetch policy/template jobs ---
def fetch_policy_push_jobs(api_key):
    url = f"https://{PANORAMA_IP}/api/"
    params = {
        "type": "op",
        "cmd": "<show><jobs><all/></jobs></show>",
        "key": api_key
    }
    try:
        response = requests.get(url, params=params, verify=False, timeout=30)
        response.raise_for_status()
        return ET.fromstring(response.text).findall(".//job")
    except Exception as e:
        print(f"Error fetching job history: {e}")
        exit(1)

# --- Function to parse and display job results ---
def parse_policy_push_outcomes(jobs):
    print("\n📋 Policy Push Outcomes:\n")
    found = False

    for job in jobs:
        job_type = job.findtext("type")
        job_status = job.findtext("status")
        job_result = job.findtext("result")

        if job_type and job_type.lower() in ["commit", "push", "template"] and job_status == "FIN":
            for entry in job.findall(".//entry"):
                devname = entry.findtext("devicename") or "Unknown"
                serial = entry.findtext("serial-no") or "-"
                status = entry.findtext("status") or "-"
                raw_result = entry.findtext("result")

                # Classify policy push outcome
                if raw_result:
                    result_clean = raw_result.strip().lower()
                    if "warning" in result_clean:
                        outcome = "SuccessWithWarnings"
                    elif "ok" in result_clean or "success" in result_clean:
                        outcome = "Success"
                    elif "fail" in result_clean:
                        outcome = "Failed"
                    else:
                        outcome = result_clean.title()
                else:
                    outcome = "Unknown"

                print(f"🔹 Device: {devname:20} | Serial: {serial:18} | Policy Push Outcome: {outcome:20} | Deployment Status: {status:12} | Job Result: {job_result}")
                found = True

    if not found:
        print("No completed commit/template jobs found.")

# --- Main execution ---
if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings()
    api_key = get_api_key()
    jobs = fetch_policy_push_jobs(api_key)
    parse_policy_push_outcomes(jobs)


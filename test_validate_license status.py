from validate_license_status import analyze_license_status
from datetime import datetime, timedelta

def future(days):
    return (datetime.today() + timedelta(days=days)).strftime("%Y/%m/%d")

def past(days):
    return (datetime.today() - timedelta(days=days)).strftime("%Y/%m/%d")

def test_valid_license():
    license_data = {
        'wildfire': {'description': 'WildFire', 'expires': future(200)}
    }
    result, expiring = analyze_license_status(license_data)
    print(result)
    print(expiring)

def test_expired_license():
    license_data = {
        'wildfire': {'description': 'WildFire', 'expires': past(5)}
    }
    result, expiring = analyze_license_status(license_data)
    print(result)
    print(expiring)

def test_expiring_soon_license():
    license_data = {
        'wildfire': {'description': 'WildFire', 'expires': future(90)}
    }
    result, expiring = analyze_license_status(license_data)
    print(result)
    print(expiring)

def test_missing_license():
    license_data = {}
    result, expiring = analyze_license_status(license_data)
    print(result)
    print(expiring)

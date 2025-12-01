"""Quick test to see API response structure"""
import requests
import json

url = "https://www.bitrefill.com/api/product/bitrefill-esim-north-america?source=esim"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json',
    'Referer': 'https://www.bitrefill.com/us/en/esims/',
    'Origin': 'https://www.bitrefill.com',
}

r = requests.get(url, headers=headers)
print(f"Status: {r.status_code}")
print(f"Response text (first 500 chars): {r.text[:500]}")
print("\n" + "="*50)
if r.status_code == 200:
    try:
        data = r.json()
        print(json.dumps(data, indent=2))
    except:
        print("Not JSON response")
else:
    print(f"Error: {r.text}")


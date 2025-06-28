#!/usr/bin/env python3
"""Network request example - demonstrates HTTP operations"""

import urllib.request
import json

def fetch_data(url):
    """Fetch data from a URL"""
    try:
        with urllib.request.urlopen(url) as response:
            data = response.read()
            return data.decode('utf-8')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def main():
    # Example: Fetch JSON placeholder data
    url = "https://jsonplaceholder.typicode.com/posts/1"
    
    print(f"Fetching data from: {url}")
    result = fetch_data(url)
    
    if result:
        # Parse JSON
        data = json.loads(result)
        print("\nReceived data:")
        print(json.dumps(data, indent=2))
        
        # Access specific fields
        print(f"\nTitle: {data.get('title', 'N/A')}")
        print(f"Body: {data.get('body', 'N/A')}")
    else:
        print("Failed to fetch data")

if __name__ == "__main__":
    main()
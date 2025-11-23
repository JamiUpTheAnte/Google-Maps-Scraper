"""Test script to debug Google search issues"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, unquote
import time
import random

print("Testing Google search with direct scraping...")
print("=" * 60)

try:
    query = "construction company Atlanta"
    print(f"Query: {query}")
    print("Attempting to search...")
    print()

    encoded_query = quote_plus(query)
    search_url = f"https://www.google.com/search?q={encoded_query}&num=10"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'DNT': '1',
    }

    response = requests.get(search_url, headers=headers, timeout=10)
    print(f"Status Code: {response.status_code}")
    print()

    soup = BeautifulSoup(response.text, 'html.parser')

    results = []
    for link in soup.find_all('a'):
        href = link.get('href', '')

        if '/url?q=' in href:
            url = href.split('/url?q=')[1].split('&')[0]
            url = unquote(url)

            if url.startswith('http') and not any(x in url.lower() for x in ['google.com', 'youtube.com', 'facebook.com', 'linkedin.com', 'yelp.com']):
                if url not in results:
                    results.append(url)
                    print(f"{len(results)}. {url}")

                if len(results) >= 5:
                    break

    print()
    print("=" * 60)
    print(f"Total results found: {len(results)}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

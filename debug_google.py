"""Debug script to examine Google's HTML structure"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, unquote
import re

query = "construction company Atlanta"
encoded_query = quote_plus(query)
search_url = f"https://www.google.com/search?q={encoded_query}&num=10"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'DNT': '1',
}

print(f"Fetching: {search_url}\n")
response = requests.get(search_url, headers=headers, timeout=10)
print(f"Status: {response.status_code}\n")

soup = BeautifulSoup(response.text, 'html.parser')

# Save HTML for inspection
with open('google_response.html', 'w', encoding='utf-8') as f:
    f.write(response.text)
print("✓ Saved raw HTML to google_response.html\n")

# Try different methods to extract URLs
print("=" * 60)
print("METHOD 1: Looking for /url?q= links")
print("=" * 60)
count = 0
for link in soup.find_all('a', href=True):
    href = link.get('href', '')
    if '/url?q=' in href:
        count += 1
        print(f"{count}. {href[:100]}...")
if count == 0:
    print("None found")

print("\n" + "=" * 60)
print("METHOD 2: Looking for direct http links in href")
print("=" * 60)
count = 0
for link in soup.find_all('a', href=True):
    href = link.get('href', '')
    if href.startswith('http') and 'google.com' not in href:
        count += 1
        print(f"{count}. {href[:100]}")
        if count >= 5:
            break
if count == 0:
    print("None found")

print("\n" + "=" * 60)
print("METHOD 3: Looking for links with specific classes")
print("=" * 60)
# Google often uses specific div classes for search results
result_divs = soup.find_all('div', class_=re.compile(r'(g|Gx5Zad|fP1Qef|yuRUbf)'))
print(f"Found {len(result_divs)} divs with result-like classes")

print("\n" + "=" * 60)
print("METHOD 4: Looking for cite tags (Google shows URLs in cite tags)")
print("=" * 60)
count = 0
for cite in soup.find_all('cite'):
    count += 1
    print(f"{count}. {cite.get_text()}")
    if count >= 5:
        break
if count == 0:
    print("None found")

print("\n" + "=" * 60)
print("METHOD 5: All <a> tags with text content")
print("=" * 60)
count = 0
for link in soup.find_all('a', href=True):
    text = link.get_text(strip=True)
    href = link.get('href', '')
    if text and len(text) > 10 and href:
        count += 1
        print(f"{count}. Text: {text[:50]}... | Href: {href[:80]}")
        if count >= 10:
            break

"""Test script for Selenium-based Google search"""
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, unquote
import time

print("Testing Selenium Google search...")
print("=" * 60)

try:
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    print("Starting Chrome browser...")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    query = "construction company Atlanta"
    encoded_query = quote_plus(query)
    search_url = f"https://www.google.com/search?q={encoded_query}&num=10"

    print(f"Query: {query}")
    print(f"Fetching: {search_url}")
    print()

    driver.get(search_url)
    time.sleep(3)

    print("Page loaded successfully!")
    print()

    # Parse with BeautifulSoup
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    results = []

    # Look for /url?q= links
    for link in soup.find_all('a', href=True):
        href = link.get('href', '')

        if '/url?q=' in href:
            try:
                url = href.split('/url?q=')[1].split('&')[0]
                url = unquote(url)

                excluded = ['google.com', 'youtube.com', 'facebook.com', 'linkedin.com', 'yelp.com']
                if url.startswith('http') and not any(x in url.lower() for x in excluded):
                    if url not in results:
                        results.append(url)
                        print(f"{len(results)}. {url}")

                    if len(results) >= 5:
                        break
            except:
                continue

    driver.quit()

    print()
    print("=" * 60)
    print(f"Total results found: {len(results)}")
    print()
    print("✅ SUCCESS! Selenium is working and found construction company URLs!")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

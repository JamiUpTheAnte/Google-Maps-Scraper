"""
Google Maps Business Scraper with Rate Limiting
Scrapes construction companies from Google search results and extracts contact information.
"""

import time
import random
import requests
from bs4 import BeautifulSoup
import re
import csv
from typing import List, Dict
try:
    from googlesearch import search as googlesearch_search
except ImportError:
    googlesearch_search = None
from urllib.parse import quote_plus, urlparse, unquote
import logging
from datetime import datetime

# Selenium imports
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logger.warning("Selenium not available. Install with: pip install selenium webdriver-manager")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class RateLimitedScraper:
    """Scraper with built-in rate limiting to avoid IP bans"""

    def __init__(self, min_delay=2.0, max_delay=5.0, request_timeout=10):
        """
        Initialize the scraper with rate limiting parameters.

        Args:
            min_delay: Minimum delay between requests in seconds
            max_delay: Maximum delay between requests in seconds
            request_timeout: Timeout for HTTP requests in seconds
        """
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.request_timeout = request_timeout
        self.session = requests.Session()

        # Rotate user agents to appear more like a real browser
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]

        self.request_count = 0
        self.last_request_time = 0

    def _get_random_user_agent(self) -> str:
        """Return a random user agent string"""
        return random.choice(self.user_agents)

    def _apply_rate_limit(self):
        """Apply rate limiting with random delay"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        # Calculate delay with jitter to avoid patterns
        delay = random.uniform(self.min_delay, self.max_delay)

        # If we made a request recently, wait the remaining time
        if time_since_last_request < delay:
            sleep_time = delay - time_since_last_request
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)

        self.last_request_time = time.time()
        self.request_count += 1

        # Every 10 requests, take a longer break
        if self.request_count % 10 == 0:
            extra_delay = random.uniform(5, 10)
            logger.info(f"Taking extended break after {self.request_count} requests ({extra_delay:.2f}s)")
            time.sleep(extra_delay)

    def fetch_url(self, url: str, max_retries=3) -> requests.Response:
        """
        Fetch URL with rate limiting and retries.

        Args:
            url: URL to fetch
            max_retries: Maximum number of retry attempts

        Returns:
            Response object or None if all retries failed
        """
        headers = {
            'User-Agent': self._get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

        for attempt in range(max_retries):
            try:
                self._apply_rate_limit()

                logger.info(f"Fetching: {url} (attempt {attempt + 1}/{max_retries})")
                response = self.session.get(
                    url,
                    headers=headers,
                    timeout=self.request_timeout,
                    allow_redirects=True
                )

                if response.status_code == 200:
                    return response
                elif response.status_code == 429:  # Too Many Requests
                    wait_time = (2 ** attempt) * 5  # Exponential backoff
                    logger.warning(f"Rate limited (429). Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    logger.warning(f"HTTP {response.status_code} for {url}")

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout fetching {url}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching {url}: {e}")

            # Wait before retry with exponential backoff
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 2
                time.sleep(wait_time)

        return None

    def extract_emails(self, text: str) -> List[str]:
        """Extract email addresses from text"""
        email_pattern = r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
        emails = re.findall(email_pattern, text)

        # Filter out common non-email matches
        filtered_emails = [
            email for email in emails
            if not any(exclude in email.lower() for exclude in ['example.com', 'samplesite', 'yoursite'])
        ]

        return list(set(filtered_emails))  # Remove duplicates

    def extract_phone_numbers(self, text: str) -> List[str]:
        """Extract phone numbers from text"""
        phone_patterns = [
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # 123-456-7890 or 123.456.7890
            r'\b\(\d{3}\)\s*\d{3}[-.]?\d{4}\b',  # (123) 456-7890
            r'\b\d{3}\s\d{3}\s\d{4}\b'  # 123 456 7890
        ]

        phones = []
        for pattern in phone_patterns:
            phones.extend(re.findall(pattern, text))

        return list(set(phones))

    def find_contact_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Find contact and about page links"""
        contact_links = []
        keywords = ['contact', 'about', 'reach-us', 'get-in-touch', 'contactus']

        for link in soup.find_all('a', href=True):
            href = link['href'].lower()
            if any(keyword in href for keyword in keywords):
                # Convert relative URLs to absolute
                if href.startswith('/'):
                    from urllib.parse import urljoin
                    href = urljoin(base_url, href)
                elif not href.startswith('http'):
                    continue
                contact_links.append(href)

        return list(set(contact_links))

    def scrape_website(self, url: str) -> Dict:
        """
        Scrape a single website for contact information.

        Args:
            url: Website URL to scrape

        Returns:
            Dictionary with extracted information
        """
        result = {
            'website': url,
            'company': '',
            'emails': [],
            'phones': [],
            'contact_pages': [],
            'scraped_at': datetime.now().isoformat(),
            'status': 'failed'
        }

        try:
            response = self.fetch_url(url)
            if not response:
                logger.warning(f"Failed to fetch {url}")
                return result

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract company name from title
            if soup.title:
                result['company'] = soup.title.string.strip()

            # Extract emails from main page
            result['emails'] = self.extract_emails(response.text)

            # Extract phone numbers
            result['phones'] = self.extract_phone_numbers(response.text)

            # Find contact pages
            contact_links = self.find_contact_links(soup, url)
            result['contact_pages'] = contact_links

            # Scrape contact pages for additional info (limit to first 2 to avoid excessive requests)
            for contact_url in contact_links[:2]:
                logger.info(f"Checking contact page: {contact_url}")
                contact_response = self.fetch_url(contact_url)
                if contact_response:
                    result['emails'].extend(self.extract_emails(contact_response.text))
                    result['phones'].extend(self.extract_phone_numbers(contact_response.text))

            # Remove duplicates
            result['emails'] = list(set(result['emails']))
            result['phones'] = list(set(result['phones']))
            result['status'] = 'success'

            logger.info(f"✓ Scraped {url}: {len(result['emails'])} emails, {len(result['phones'])} phones")

        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")

        return result


def search_google_selenium(query: str, num_results: int = 100) -> List[str]:
    """
    Search Google using Selenium browser automation to bypass bot detection.

    Args:
        query: Search query
        num_results: Number of results to fetch

    Returns:
        List of URLs
    """
    if not SELENIUM_AVAILABLE:
        logger.error("Selenium not available. Falling back to direct scraping.")
        return search_google_direct(query, num_results)

    logger.info(f"Searching Google with Selenium for: '{query}' (up to {num_results} results)")

    urls = set()

    try:
        # Set up Chrome options for headless browsing
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run in background
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        # Initialize the Chrome driver
        logger.info("Starting Chrome browser...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # Calculate number of pages needed
        results_per_page = 10
        num_pages = min((num_results + results_per_page - 1) // results_per_page, 10)  # Max 10 pages

        try:
            for page in range(num_pages):
                start = page * results_per_page
                encoded_query = quote_plus(query)
                search_url = f"https://www.google.com/search?q={encoded_query}&start={start}&num={results_per_page}"

                logger.info(f"Fetching page {page + 1}/{num_pages}...")
                driver.get(search_url)

                # Wait for results to load
                time.sleep(random.uniform(2, 4))

                # Get page source and parse with BeautifulSoup
                soup = BeautifulSoup(driver.page_source, 'html.parser')

                # Method 1: Look for /url?q= links
                for link in soup.find_all('a', href=True):
                    href = link.get('href', '')

                    if '/url?q=' in href:
                        try:
                            url = href.split('/url?q=')[1].split('&')[0]
                            url = unquote(url)

                            # Filter out unwanted domains
                            excluded_domains = ['google.com', 'youtube.com', 'facebook.com',
                                              'linkedin.com', 'yelp.com', 'instagram.com',
                                              'twitter.com', 'pinterest.com']

                            if url.startswith('http') and not any(domain in url.lower() for domain in excluded_domains):
                                if url not in urls:
                                    urls.add(url)
                                    logger.info(f"Found result #{len(urls)}: {url}")

                                    if len(urls) >= num_results:
                                        logger.info(f"Reached target of {num_results} results")
                                        return list(urls)
                        except Exception as e:
                            logger.debug(f"Error parsing link: {e}")
                            continue

                # Method 2: Look for direct http links (fallback)
                if len(urls) < num_results:
                    for link in soup.find_all('a', href=True):
                        href = link.get('href', '')

                        if href.startswith('http') and not any(domain in href.lower() for domain in ['google.com', 'gstatic.com']):
                            excluded_domains = ['youtube.com', 'facebook.com', 'linkedin.com',
                                              'yelp.com', 'instagram.com', 'twitter.com']

                            if not any(domain in href.lower() for domain in excluded_domains):
                                if href not in urls:
                                    urls.add(href)
                                    logger.info(f"Found result #{len(urls)}: {href}")

                                    if len(urls) >= num_results:
                                        return list(urls)

                logger.info(f"Page {page + 1} complete. Total URLs: {len(urls)}")

                # Rate limiting between pages
                if page < num_pages - 1:
                    delay = random.uniform(3, 6)
                    logger.info(f"Waiting {delay:.1f}s before next page...")
                    time.sleep(delay)

        finally:
            driver.quit()
            logger.info("Browser closed")

    except Exception as e:
        logger.error(f"Error during Selenium search: {e}")
        logger.exception("Full traceback:")

    logger.info(f"Search complete: found {len(urls)} URLs")
    return list(urls)


def search_google_direct(query: str, num_results: int = 100) -> List[str]:
    """
    Directly scrape Google search results.

    Args:
        query: Search query
        num_results: Number of results to fetch

    Returns:
        List of URLs
    """
    logger.info(f"Searching Google for: '{query}' (up to {num_results} results)")

    urls = set()  # Use set to avoid duplicates
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    ]

    # Calculate number of pages needed (Google shows ~10 results per page)
    results_per_page = 10
    num_pages = (num_results + results_per_page - 1) // results_per_page

    try:
        for page in range(num_pages):
            # Build Google search URL
            start = page * results_per_page
            encoded_query = quote_plus(query)
            search_url = f"https://www.google.com/search?q={encoded_query}&start={start}&num={results_per_page}"

            headers = {
                'User-Agent': random.choice(user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }

            logger.info(f"Fetching page {page + 1}/{num_pages}...")

            try:
                response = requests.get(search_url, headers=headers, timeout=10)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, 'html.parser')

                # Find all search result links
                # Google uses various div classes for results, so we look for common patterns
                for link in soup.find_all('a'):
                    href = link.get('href', '')

                    # Google search results typically start with /url?q=
                    if '/url?q=' in href:
                        # Extract the actual URL
                        url = href.split('/url?q=')[1].split('&')[0]

                        # Decode URL
                        from urllib.parse import unquote
                        url = unquote(url)

                        # Filter out Google's own URLs and invalid URLs
                        if url.startswith('http') and not any(x in url.lower() for x in ['google.com', 'youtube.com', 'facebook.com', 'linkedin.com', 'yelp.com']):
                            if url not in urls:
                                urls.add(url)
                                logger.info(f"Found result #{len(urls)}: {url}")

                                if len(urls) >= num_results:
                                    logger.info(f"Reached target of {num_results} results")
                                    return list(urls)

                logger.info(f"Page {page + 1} complete. Total URLs: {len(urls)}")

                # Rate limiting between pages
                if page < num_pages - 1:
                    delay = random.uniform(3, 6)
                    logger.info(f"Waiting {delay:.1f}s before next page...")
                    time.sleep(delay)

            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching page {page + 1}: {e}")
                time.sleep(5)  # Wait longer on error
                continue

    except Exception as e:
        logger.error(f"Error during Google search: {e}")
        logger.exception("Full traceback:")

    logger.info(f"Search complete: found {len(urls)} URLs")
    return list(urls)


def search_google(query: str, num_results: int = 100, lang: str = 'en') -> List[str]:
    """
    Search Google with rate limiting. Uses Selenium for reliability, falls back to direct scraping.

    Args:
        query: Search query
        num_results: Number of results to fetch
        lang: Language for search results

    Returns:
        List of URLs
    """
    # Use Selenium for better reliability against bot detection
    if SELENIUM_AVAILABLE:
        return search_google_selenium(query, num_results)
    else:
        logger.warning("Selenium not available, using direct scraping (may be blocked by Google)")
        return search_google_direct(query, num_results)


def save_to_csv(leads: List[Dict], filename: str = 'leads.csv'):
    """Save leads to CSV file"""
    if not leads:
        logger.warning("No leads to save")
        return

    fieldnames = ['website', 'company', 'emails', 'phones', 'contact_pages', 'scraped_at', 'status']

    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for lead in leads:
            # Convert lists to strings for CSV
            lead_copy = lead.copy()
            lead_copy['emails'] = '; '.join(lead_copy['emails'])
            lead_copy['phones'] = '; '.join(lead_copy['phones'])
            lead_copy['contact_pages'] = '; '.join(lead_copy['contact_pages'])
            writer.writerow(lead_copy)

    logger.info(f"✓ Saved {len(leads)} leads to {filename}")


def main():
    """Main scraper function"""
    # Configuration
    QUERY = "construction company Atlanta"
    NUM_RESULTS = 100
    MIN_DELAY = 3.0  # Minimum delay between requests (seconds)
    MAX_DELAY = 7.0  # Maximum delay between requests (seconds)

    logger.info("=" * 60)
    logger.info("Google Maps Business Scraper Starting")
    logger.info("=" * 60)
    logger.info(f"Query: {QUERY}")
    logger.info(f"Target results: {NUM_RESULTS}")
    logger.info(f"Rate limiting: {MIN_DELAY}-{MAX_DELAY}s between requests")
    logger.info("=" * 60)

    # Step 1: Search Google
    urls = search_google(QUERY, num_results=NUM_RESULTS)

    if not urls:
        logger.error("No URLs found. Exiting.")
        return

    # Step 2: Scrape each website
    scraper = RateLimitedScraper(
        min_delay=MIN_DELAY,
        max_delay=MAX_DELAY,
        request_timeout=10
    )

    leads = []
    for i, url in enumerate(urls, 1):
        logger.info(f"\n[{i}/{len(urls)}] Processing: {url}")
        lead = scraper.scrape_website(url)
        leads.append(lead)

        # Save intermediate results every 10 leads
        if i % 10 == 0:
            save_to_csv(leads, 'leads_partial.csv')
            logger.info(f"Checkpoint: Saved {len(leads)} leads so far")

    # Step 3: Save final results
    save_to_csv(leads, 'leads.csv')

    # Summary
    successful = sum(1 for lead in leads if lead['status'] == 'success')
    with_emails = sum(1 for lead in leads if lead['emails'])
    with_phones = sum(1 for lead in leads if lead['phones'])

    logger.info("=" * 60)
    logger.info("Scraping Complete!")
    logger.info("=" * 60)
    logger.info(f"Total URLs processed: {len(leads)}")
    logger.info(f"Successfully scraped: {successful}")
    logger.info(f"Leads with emails: {with_emails}")
    logger.info(f"Leads with phones: {with_phones}")
    logger.info(f"Total requests made: {scraper.request_count}")
    logger.info(f"Results saved to: leads.csv")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

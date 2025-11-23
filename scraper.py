"""
Yelp Business Scraper for Construction Companies
Scrapes construction companies from Yelp and extracts contact information.
Uses Selenium for Yelp to bypass 403 blocking.
"""

import time
import random
import requests
from bs4 import BeautifulSoup
import re
import csv
import json
from typing import List, Dict
from urllib.parse import quote_plus, urljoin, urlparse, parse_qs, unquote
import logging
from datetime import datetime

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Selenium imports
try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logger.warning("Selenium not available. Install with: pip install selenium undetected-chromedriver")


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

                logger.debug(f"Fetching: {url} (attempt {attempt + 1}/{max_retries})")
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
                    href = urljoin(base_url, href)
                elif not href.startswith('http'):
                    continue
                contact_links.append(href)

        return list(set(contact_links))

    def scrape_website(self, url: str, company_name: str = '', yelp_phone: str = '') -> Dict:
        """
        Scrape a single website for contact information.

        Args:
            url: Website URL to scrape
            company_name: Company name from Yelp
            yelp_phone: Phone number from Yelp

        Returns:
            Dictionary with extracted information
        """
        result = {
            'website': url,
            'company': company_name,
            'emails': [],
            'phones': [yelp_phone] if yelp_phone else [],
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

            # Extract company name from title if not provided
            if not result['company'] and soup.title:
                result['company'] = soup.title.string.strip()

            # Extract emails from main page
            result['emails'] = self.extract_emails(response.text)

            # Extract phone numbers
            phones = self.extract_phone_numbers(response.text)
            result['phones'].extend(phones)
            result['phones'] = list(set(result['phones']))  # Remove duplicates

            # Find contact pages
            contact_links = self.find_contact_links(soup, url)
            result['contact_pages'] = contact_links

            # Scrape contact pages for additional info (limit to first 2)
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


def search_yelp(category: str, location: str, num_results: int = 100) -> List[Dict]:
    """
    Search Yelp for businesses using Selenium to bypass 403 blocking.

    Args:
        category: Business category (e.g., "construction", "general contractors")
        location: Location to search (e.g., "Atlanta, GA")
        num_results: Number of results to fetch

    Returns:
        List of business dictionaries with name, website, phone
    """
    if not SELENIUM_AVAILABLE:
        logger.error("Selenium is required to scrape Yelp. Install with: pip install selenium webdriver-manager")
        return []

    logger.info(f"Searching Yelp for '{category}' in '{location}' (up to {num_results} results)")

    businesses = []

    # Yelp shows 10 results per page
    results_per_page = 10
    num_pages = (num_results + results_per_page - 1) // results_per_page

    try:
        # Initialize undetected Chrome driver
        logger.info("Starting undetected Chrome browser...")

        # Check for manual driver path
        import os
        manual_driver_path = r"C:\chromedriver\chromedriver.exe"

        if os.path.exists(manual_driver_path):
            logger.info(f"Using manual chromedriver from: {manual_driver_path}")
            driver = uc.Chrome(driver_executable_path=manual_driver_path, headless=False, use_subprocess=True)
        else:
            logger.info("Using auto-managed chromedriver...")
            driver = uc.Chrome(headless=False, use_subprocess=True)

        try:
            for page in range(num_pages):
                start = page * results_per_page

                # Build Yelp search URL
                search_url = f"https://www.yelp.com/search?find_desc={quote_plus(category)}&find_loc={quote_plus(location)}&start={start}"

                logger.info(f"Fetching Yelp page {page + 1}/{num_pages}...")
                driver.get(search_url)

                # Wait for page to load
                time.sleep(random.uniform(3, 5))

                # Get page source and parse with BeautifulSoup
                soup = BeautifulSoup(driver.page_source, 'html.parser')

                # DEBUG: Save the HTML to inspect what we're getting
                if page == 0:  # Save first page for debugging
                    with open('yelp_page_debug.html', 'w', encoding='utf-8') as f:
                        f.write(driver.page_source)
                    logger.info("Saved first page HTML to yelp_page_debug.html for inspection")

                # Find business listings - Yelp uses JSON-LD structured data
                scripts = soup.find_all('script', type='application/ld+json')
                logger.info(f"Found {len(scripts)} JSON-LD scripts on page")
                for script in scripts:
                    try:
                        data = json.loads(script.string)
                        if isinstance(data, list):
                            for item in data:
                                if item.get('@type') == 'LocalBusiness':
                                    business = {
                                        'name': item.get('name', ''),
                                        'phone': item.get('telephone', ''),
                                        'website': '',
                                        'yelp_url': ''
                                    }
                                    businesses.append(business)
                    except (json.JSONDecodeError, AttributeError):
                        continue

                # Also scrape business cards directly from HTML
                business_cards = soup.find_all('div', {'data-testid': re.compile(r'serp-ia-card')}) or \
                               soup.find_all('div', class_=re.compile(r'container.*mainContent'))

                logger.info(f"Found {len(business_cards)} business card divs")

                # Try alternative selectors if no cards found
                if len(business_cards) == 0:
                    # Look for any links with /biz/ in them (business pages)
                    biz_links = soup.find_all('a', href=re.compile(r'/biz/'))
                    logger.info(f"Found {len(biz_links)} business links as fallback")

                    # DEBUG: Show sample of what we're finding
                    if biz_links:
                        sample_link = biz_links[0]
                        logger.info(f"Sample link text: '{sample_link.get_text(strip=True)[:50]}'")
                        logger.info(f"Sample link href: '{sample_link.get('href', '')[:80]}'")
                        logger.info(f"Sample link aria-label: '{sample_link.get('aria-label', '')[:50]}'")

                    # Extract business info from these links
                    seen_urls = set()
                    for link in biz_links:
                        try:
                            href = link.get('href', '')
                            if not href or '/biz/' not in href:
                                continue

                            # Build full Yelp URL
                            yelp_url = urljoin('https://www.yelp.com', href.split('?')[0])  # Remove query params

                            # Skip duplicates
                            if yelp_url in seen_urls:
                                continue
                            seen_urls.add(yelp_url)

                            # Try multiple strategies to get business name
                            name = None

                            # Strategy 1: Check if this link itself has the business name
                            link_text = link.get_text(strip=True)
                            if link_text and len(link_text) >= 3 and len(link_text) <= 100:
                                # Filter out common non-name texts
                                skip_texts = ['read more', 'see all', 'photos', 'reviews', 'website',
                                            'directions', 'call', 'menu', 'write a review', 'get directions']
                                if not any(skip in link_text.lower() for skip in skip_texts):
                                    name = link_text

                            # Strategy 2: Check aria-label attribute
                            if not name:
                                aria_label = link.get('aria-label', '')
                                if aria_label and len(aria_label) >= 3 and len(aria_label) <= 100:
                                    name = aria_label

                            # Strategy 3: Look for h3/h4/h2 in the link's parent containers
                            if not name:
                                parent = link.parent
                                for _ in range(3):  # Check up to 3 parent levels
                                    if parent:
                                        # Look for heading tags
                                        heading = parent.find(['h3', 'h4', 'h2', 'h1'])
                                        if heading:
                                            heading_text = heading.get_text(strip=True)
                                            if heading_text and len(heading_text) >= 3 and len(heading_text) <= 100:
                                                name = heading_text
                                                break
                                        parent = parent.parent
                                    else:
                                        break

                            # Strategy 4: Look for name in sibling elements
                            if not name and link.parent:
                                for sibling in link.parent.find_all(['h3', 'h4', 'h2', 'span', 'div'], limit=5):
                                    sibling_text = sibling.get_text(strip=True)
                                    if sibling_text and len(sibling_text) >= 3 and len(sibling_text) <= 100:
                                        skip_texts = ['read more', 'see all', 'photos', 'reviews', 'website']
                                        if not any(skip in sibling_text.lower() for skip in skip_texts):
                                            name = sibling_text
                                            break

                            if name and len(name) >= 3:
                                # Clean up the name (remove extra whitespace, newlines)
                                name = ' '.join(name.split())

                                # Check if not already in list
                                if not any(b.get('yelp_url') == yelp_url for b in businesses):
                                    businesses.append({
                                        'name': name,
                                        'phone': '',
                                        'website': '',
                                        'yelp_url': yelp_url
                                    })
                                    logger.info(f"Found business: {name} ({yelp_url})")

                                    if len(businesses) >= num_results:
                                        break
                        except Exception as e:
                            logger.debug(f"Error parsing biz link: {e}")
                            continue

                for card in business_cards[:results_per_page]:
                    try:
                        # Extract business name
                        name_elem = card.find('a', class_=re.compile(r'business-name')) or \
                                  card.find('h3') or card.find('h2')
                        name = name_elem.get_text(strip=True) if name_elem else ''

                        # Extract phone
                        phone_elem = card.find(text=re.compile(r'\(\d{3}\)|\d{3}-\d{3}-\d{4}'))
                        phone = phone_elem.strip() if phone_elem else ''

                        # Extract Yelp URL
                        link_elem = card.find('a', href=re.compile(r'/biz/'))
                        yelp_url = urljoin('https://www.yelp.com', link_elem['href']) if link_elem else ''

                        if name and (phone or yelp_url):
                            # Check if not already in list
                            if not any(b['name'] == name for b in businesses):
                                businesses.append({
                                    'name': name,
                                    'phone': phone,
                                    'website': '',
                                    'yelp_url': yelp_url
                                })
                                logger.info(f"Found business: {name}")

                    except Exception as e:
                        logger.debug(f"Error parsing business card: {e}")
                        continue

                logger.info(f"Page {page + 1} complete. Total businesses: {len(businesses)}")

                if len(businesses) >= num_results:
                    businesses = businesses[:num_results]
                    break

                # Rate limiting between pages
                if page < num_pages - 1:
                    time.sleep(random.uniform(3, 6))

            # Now fetch website URLs from Yelp business pages using Selenium
            logger.info(f"\nFetching website URLs for {len(businesses)} businesses...")
            for i, business in enumerate(businesses, 1):
                if business['yelp_url']:
                    try:
                        logger.info(f"[{i}/{len(businesses)}] Fetching website for {business['name']}...")
                        driver.get(business['yelp_url'])
                        time.sleep(random.uniform(2, 4))

                        soup = BeautifulSoup(driver.page_source, 'html.parser')

                        # Look for website link
                        website_link = soup.find('a', text=re.compile(r'Business website', re.I)) or \
                                     soup.find('a', href=re.compile(r'biz_redir'))
                        if website_link and website_link.get('href'):
                            # Yelp redirects, extract actual URL
                            href = website_link['href']
                            if 'url=' in href:
                                parsed = parse_qs(urlparse(href).query)
                                if 'url' in parsed:
                                    business['website'] = unquote(parsed['url'][0])
                            elif href.startswith('http'):
                                business['website'] = href

                            if business['website']:
                                logger.info(f"  ✓ Found website: {business['website']}")
                    except Exception as e:
                        logger.warning(f"  Error fetching website for {business['name']}: {e}")
                        continue

        finally:
            driver.quit()
            logger.info("Browser closed")

    except Exception as e:
        logger.error(f"Error during Yelp search: {e}")
        logger.exception("Full traceback:")

    logger.info(f"Yelp search complete: found {len(businesses)} businesses")
    return businesses


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
            lead_copy['emails'] = '; '.join(lead_copy.get('emails', []))
            lead_copy['phones'] = '; '.join(lead_copy.get('phones', []))
            lead_copy['contact_pages'] = '; '.join(lead_copy.get('contact_pages', []))
            writer.writerow(lead_copy)

    logger.info(f"✓ Saved {len(leads)} leads to {filename}")


def save_to_json(leads: List[Dict], filename: str = 'leads.json'):
    """Save leads to JSON file"""
    if not leads:
        logger.warning("No leads to save")
        return

    with open(filename, 'w', encoding='utf-8') as jsonfile:
        json.dump(leads, jsonfile, indent=2, default=str)

    logger.info(f"✓ Saved {len(leads)} leads to {filename}")


def main():
    """Main scraper function"""
    # Configuration
    CATEGORY = "general contractors"  # or "construction company"
    LOCATION = "Atlanta, GA"
    NUM_RESULTS = 50  # Number of businesses to find on Yelp
    MIN_DELAY = 3.0  # Minimum delay between requests (seconds)
    MAX_DELAY = 7.0  # Maximum delay between requests (seconds)

    logger.info("=" * 70)
    logger.info("YELP CONSTRUCTION COMPANY LEAD SCRAPER")
    logger.info("=" * 70)
    logger.info(f"Category: {CATEGORY}")
    logger.info(f"Location: {LOCATION}")
    logger.info(f"Target businesses: {NUM_RESULTS}")
    logger.info(f"Rate limiting: {MIN_DELAY}-{MAX_DELAY}s between requests")
    logger.info("=" * 70)

    # Step 1: Search Yelp for businesses
    businesses = search_yelp(CATEGORY, LOCATION, num_results=NUM_RESULTS)

    if not businesses:
        logger.error("No businesses found. Exiting.")
        return

    logger.info(f"\n✓ Found {len(businesses)} businesses on Yelp")
    logger.info(f"Businesses with websites: {sum(1 for b in businesses if b['website'])}")

    # Step 2: Scrape each website for contact info
    scraper = RateLimitedScraper(
        min_delay=MIN_DELAY,
        max_delay=MAX_DELAY,
        request_timeout=10
    )

    leads = []
    for i, business in enumerate(businesses, 1):
        if business['website']:
            logger.info(f"\n[{i}/{len(businesses)}] Processing: {business['name']}")
            lead = scraper.scrape_website(
                business['website'],
                company_name=business['name'],
                yelp_phone=business['phone']
            )
            leads.append(lead)

            # Save intermediate results every 10 leads
            if i % 10 == 0:
                save_to_csv(leads, 'leads_partial.csv')
                logger.info(f"Checkpoint: Saved {len(leads)} leads so far")
        else:
            # Save business info even without website
            leads.append({
                'website': '',
                'company': business['name'],
                'emails': [],
                'phones': [business['phone']] if business['phone'] else [],
                'contact_pages': [],
                'scraped_at': datetime.now().isoformat(),
                'status': 'no_website'
            })
            logger.info(f"[{i}/{len(businesses)}] {business['name']} - No website found")

    # Step 3: Save final results
    save_to_csv(leads, 'leads.csv')
    save_to_json(leads, 'leads.json')

    # Summary
    successful = sum(1 for lead in leads if lead['status'] == 'success')
    with_emails = sum(1 for lead in leads if lead.get('emails'))
    with_phones = sum(1 for lead in leads if lead.get('phones'))
    with_websites = sum(1 for lead in leads if lead.get('website'))

    logger.info("=" * 70)
    logger.info("SCRAPING COMPLETE!")
    logger.info("=" * 70)
    logger.info(f"Total businesses processed: {len(leads)}")
    logger.info(f"Businesses with websites: {with_websites}")
    logger.info(f"Successfully scraped: {successful}")
    logger.info(f"Leads with emails: {with_emails}")
    logger.info(f"Leads with phones: {with_phones}")
    logger.info(f"Total requests made: {scraper.request_count}")
    logger.info(f"Results saved to: leads.csv and leads.json")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()

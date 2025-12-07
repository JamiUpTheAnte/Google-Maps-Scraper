"""
Google Maps Business Scraper with Rate Limiting and Lead Enrichment
Scrapes construction companies from Google search results and extracts contact information.
Enhanced with email quality filtering, leadership detection, and email verification.
"""

import time
import random
import requests
from bs4 import BeautifulSoup
import re
import csv
from typing import List, Dict, Optional
from googlesearch import search
import logging
from datetime import datetime
import os

# Import enrichment modules
from modules.lead_enricher import LeadEnrichmentPipeline
from modules.email_filters import filter_emails, extract_emails

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

    def __init__(self, min_delay=2.0, max_delay=5.0, request_timeout=10,
                 enable_enrichment=False, mailbox_api_key=None):
        """
        Initialize the scraper with rate limiting parameters.

        Args:
            min_delay: Minimum delay between requests in seconds
            max_delay: Maximum delay between requests in seconds
            request_timeout: Timeout for HTTP requests in seconds
            enable_enrichment: Enable lead enrichment pipeline
            mailbox_api_key: MailboxLayer API key for email verification
        """
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.request_timeout = request_timeout
        self.session = requests.Session()

        # Initialize enrichment pipeline if enabled
        self.enable_enrichment = enable_enrichment
        self.enrichment_pipeline = None

        if enable_enrichment:
            self.enrichment_pipeline = LeadEnrichmentPipeline(
                rate_limiter=self,
                mailbox_api_key=mailbox_api_key,
                enable_email_verification=mailbox_api_key is not None
            )
            logger.info("Lead enrichment pipeline enabled")

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

    def scrape_website(self, url: str, company: str = None, phone: str = None,
                      location: str = None) -> Dict:
        """
        Scrape a single website for contact information.
        Uses enrichment pipeline if enabled, otherwise falls back to basic scraping.

        Args:
            url: Website URL to scrape
            company: Company name (optional, used for enrichment)
            phone: Phone number (optional)
            location: Location (optional)

        Returns:
            Dictionary with extracted information
        """
        # Use enrichment pipeline if enabled
        if self.enable_enrichment and self.enrichment_pipeline:
            return self.scrape_website_enriched(url, company, phone, location)

        # Fallback to basic scraping
        return self.scrape_website_basic(url)

    def scrape_website_enriched(self, url: str, company: str = None,
                               phone: str = None, location: str = None) -> Dict:
        """
        Scrape website using enrichment pipeline.

        Args:
            url: Website URL
            company: Company name
            phone: Phone number
            location: Location

        Returns:
            Enriched lead data
        """
        logger.info(f"Using enrichment pipeline for: {url}")
        return self.enrichment_pipeline.enrich_lead(
            website_url=url,
            company_name=company,
            phone=phone,
            location=location
        )

    def scrape_website_basic(self, url: str) -> Dict:
        """
        Basic scraping without enrichment (backward compatible).

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


def search_google(query: str, num_results: int = 100, lang: str = 'en') -> List[str]:
    """
    Search Google with rate limiting.

    Args:
        query: Search query
        num_results: Number of results to fetch
        lang: Language for search results

    Returns:
        List of URLs
    """
    logger.info(f"Searching Google for: '{query}' (up to {num_results} results)")

    urls = []
    try:
        # Search Google and add manual rate limiting
        for url in search(query, num_results=num_results, lang=lang):
            urls.append(url)
            logger.info(f"Found result #{len(urls)}: {url}")

            # Add delay between each result to avoid rate limiting
            time.sleep(random.uniform(2, 4))

            # Add extra delay every 10 results
            if len(urls) % 10 == 0:
                logger.info(f"Retrieved {len(urls)} results, taking a break...")
                time.sleep(random.uniform(3, 6))

    except Exception as e:
        logger.error(f"Error during Google search: {e}")

    logger.info(f"Search complete: found {len(urls)} URLs")
    return urls


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

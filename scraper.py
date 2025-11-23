"""
Google Maps Construction Company Lead Scraper
Finds construction companies and their contact emails without getting IP banned.
Robust, saves results to JSON, callable from n8n automation tool.
"""

import time
import random
import requests
from bs4 import BeautifulSoup
import re
import json
from typing import List, Dict, Set
from googlesearch import search
from datetime import datetime
from urllib.parse import urljoin, urlparse

# ============================================================================
# CONFIGURATION - Easily configurable parameters
# ============================================================================
SEARCH_QUERY = "construction company Atlanta"
MAX_RESULTS = 50  # Limit to max 50 companies per run
MIN_DELAY = 2  # Minimum delay between requests (seconds)
MAX_DELAY = 5  # Maximum delay between requests (seconds)
CONTACT_PAGE_DELAY_MIN = 5  # Delay before visiting contact pages (seconds)
CONTACT_PAGE_DELAY_MAX = 10
REQUEST_TIMEOUT = 10  # Request timeout (seconds)
OUTPUT_FILE = "leads.json"

# Garbage emails to filter out
GARBAGE_EMAIL_PATTERNS = [
    'noreply@',
    'no-reply@',
    'abuse@',
    'postmaster@',
    'privacy@',
    'support@',
    'webmaster@',
    'donotreply@',
    'no_reply@'
]

# User agents for rotation (10 common browsers)
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15'
]

# Safety thresholds
CONSECUTIVE_FAILURE_WARNING = 5
CONSECUTIVE_FAILURE_STOP = 20

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def validate_email(email: str) -> bool:
    """
    Validate email format with basic check.

    Args:
        email: Email address to validate

    Returns:
        True if email has valid format, False otherwise
    """
    if not email or '@' not in email or '.' not in email:
        return False

    # Basic email pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def filter_garbage_emails(emails: Set[str]) -> Set[str]:
    """
    Remove unwanted garbage emails from the set.

    Args:
        emails: Set of email addresses

    Returns:
        Filtered set with garbage emails removed
    """
    filtered = set()

    for email in emails:
        email_lower = email.lower()

        # Check if email contains any garbage patterns
        is_garbage = any(pattern in email_lower for pattern in GARBAGE_EMAIL_PATTERNS)

        if not is_garbage and validate_email(email):
            filtered.add(email)

    return filtered


def extract_domain(url: str) -> str:
    """
    Extract domain from URL.

    Args:
        url: Full URL

    Returns:
        Domain name (e.g., 'example.com')
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


def match_email_to_domain(emails: Set[str], domain: str) -> List[str]:
    """
    Prioritize emails that match the company domain.

    Args:
        emails: Set of email addresses
        domain: Company domain

    Returns:
        List of emails, with domain-matching emails first
    """
    if not domain:
        return list(emails)

    matching = []
    other = []

    for email in emails:
        if domain in email.lower():
            matching.append(email)
        else:
            other.append(email)

    return matching + other


def scrape_emails_from_url(url: str, timeout: int = REQUEST_TIMEOUT) -> Set[str]:
    """
    Scrape emails from a single URL.

    Args:
        url: URL to scrape
        timeout: Request timeout in seconds

    Returns:
        Set of email addresses found
    """
    emails = set()

    try:
        # Random user agent
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
        }

        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)

        if response.status_code == 200:
            # Extract emails using regex
            email_pattern = r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
            found_emails = re.findall(email_pattern, response.text)
            emails.update(found_emails)

    except requests.exceptions.Timeout:
        print(f"  ⚠ Timeout scraping {url}")
    except requests.exceptions.ConnectionError:
        print(f"  ⚠ Connection error scraping {url}")
    except requests.exceptions.RequestException as e:
        print(f"  ⚠ Request error scraping {url}: {e}")
    except Exception as e:
        print(f"  ⚠ Unexpected error scraping {url}: {e}")

    return emails


def find_contact_pages(soup: BeautifulSoup, base_url: str) -> List[str]:
    """
    Find contact and about page URLs from parsed HTML.

    Args:
        soup: BeautifulSoup parsed HTML
        base_url: Base URL of the website

    Returns:
        List of contact page URLs (up to 2)
    """
    contact_urls = []
    contact_keywords = ['/contact', '/about', '/contact-us', '/reach-us', '/get-in-touch', '/contactus']

    try:
        for link in soup.find_all('a', href=True):
            href = link['href'].lower()

            # Check if href contains contact keywords
            if any(keyword in href for keyword in contact_keywords):
                # Convert relative URLs to absolute
                if href.startswith('/'):
                    full_url = urljoin(base_url, href)
                elif href.startswith('http'):
                    full_url = href
                else:
                    continue

                if full_url not in contact_urls:
                    contact_urls.append(full_url)

                # Limit to 2 contact pages
                if len(contact_urls) >= 2:
                    break

    except Exception as e:
        print(f"  ⚠ Error finding contact pages: {e}")

    return contact_urls


def scrape_company(url: str) -> Dict:
    """
    Main scraping logic for one company.

    Args:
        url: Company website URL

    Returns:
        Dictionary with company data
    """
    result = {
        'company_name': '',
        'website': url,
        'emails': [],
        'scraped_at': datetime.now().isoformat(),
        'success': False
    }

    try:
        # Apply delay before request
        delay = random.uniform(MIN_DELAY, MAX_DELAY)
        time.sleep(delay)

        print(f"  → Scraping main page: {url}")

        # Scrape main page
        all_emails = scrape_emails_from_url(url)

        # Get page content for extracting title and contact links
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }

        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT, allow_redirects=True)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract company name from title
            if soup.title and soup.title.string:
                result['company_name'] = soup.title.string.strip()
            else:
                result['company_name'] = extract_domain(url)

            # Find contact pages
            contact_pages = find_contact_pages(soup, url)

            if contact_pages:
                print(f"  → Found {len(contact_pages)} contact page(s)")

                # Delay before visiting contact pages (5-10 seconds)
                contact_delay = random.uniform(CONTACT_PAGE_DELAY_MIN, CONTACT_PAGE_DELAY_MAX)
                print(f"  ⏳ Waiting {contact_delay:.1f}s before visiting contact pages...")
                time.sleep(contact_delay)

                # Scrape contact pages
                for contact_url in contact_pages:
                    print(f"  → Scraping contact page: {contact_url}")
                    contact_emails = scrape_emails_from_url(contact_url)
                    all_emails.update(contact_emails)

                    # Small delay between contact pages
                    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

            # Filter garbage emails
            filtered_emails = filter_garbage_emails(all_emails)

            # Match emails to domain
            domain = extract_domain(url)
            result['emails'] = match_email_to_domain(filtered_emails, domain)

            result['success'] = True
            print(f"  ✓ Found {len(result['emails'])} valid email(s)")

        else:
            print(f"  ⚠ HTTP {response.status_code}")

    except requests.exceptions.Timeout:
        print(f"  ⚠ Timeout")
    except requests.exceptions.ConnectionError:
        print(f"  ⚠ Connection error")
    except requests.exceptions.RequestException as e:
        print(f"  ⚠ Request error: {e}")
    except Exception as e:
        print(f"  ⚠ Error: {e}")

    return result


def main():
    """
    Main function that orchestrates the scraping process.
    """
    print("=" * 70)
    print("CONSTRUCTION COMPANY LEAD SCRAPER")
    print("=" * 70)
    print(f"Search Query: {SEARCH_QUERY}")
    print(f"Max Results: {MAX_RESULTS}")
    print(f"Delay Between Requests: {MIN_DELAY}-{MAX_DELAY}s")
    print(f"Output File: {OUTPUT_FILE}")
    print("=" * 70)
    print()

    # Step 1: Search Google
    print(f"🔍 Searching Google for: '{SEARCH_QUERY}'...")
    print()

    urls = []
    try:
        for url in search(SEARCH_QUERY, num_results=MAX_RESULTS, lang='en', pause=2.0):
            urls.append(url)
            print(f"  [{len(urls)}] {url}")

            # Extra delay every 10 results
            if len(urls) % 10 == 0:
                time.sleep(random.uniform(3, 5))

    except Exception as e:
        print(f"⚠ Google search error: {e}")
        if not urls:
            print("❌ No URLs found. Exiting.")
            return

    print()
    print(f"✓ Found {len(urls)} URLs")
    print()
    print("=" * 70)
    print("SCRAPING COMPANIES")
    print("=" * 70)
    print()

    # Step 2: Scrape each company
    leads = []
    consecutive_failures = 0

    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] {url}")

        result = scrape_company(url)
        leads.append(result)

        # Track consecutive failures
        if not result['success']:
            consecutive_failures += 1

            # Warning at 5 consecutive failures
            if consecutive_failures == CONSECUTIVE_FAILURE_WARNING:
                print()
                print("⚠" * 30)
                print(f"WARNING: {consecutive_failures} consecutive failures detected!")
                print("Possible IP ban or network issues.")
                print("⚠" * 30)
                print()

            # Stop at 20 consecutive failures
            if consecutive_failures >= CONSECUTIVE_FAILURE_STOP:
                print()
                print("❌" * 30)
                print(f"STOPPING: {consecutive_failures} consecutive failures!")
                print("Likely IP banned or severe network issues.")
                print("❌" * 30)
                print()
                break
        else:
            consecutive_failures = 0  # Reset on success

        print()

    # Step 3: Save results to JSON
    print("=" * 70)
    print("SAVING RESULTS")
    print("=" * 70)

    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(leads, f, indent=2, ensure_ascii=False)
        print(f"✓ Saved to {OUTPUT_FILE}")
    except Exception as e:
        print(f"❌ Error saving file: {e}")

    # Step 4: Print summary
    total_companies = len(leads)
    successful_companies = sum(1 for lead in leads if lead['success'])
    companies_with_emails = sum(1 for lead in leads if lead['emails'])
    total_emails = sum(len(lead['emails']) for lead in leads)

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Found {companies_with_emails} companies with {total_emails} total emails")
    print(f"Total companies processed: {total_companies}")
    print(f"Successfully scraped: {successful_companies}")
    print(f"Failed: {total_companies - successful_companies}")
    print("=" * 70)


if __name__ == "__main__":
    main()

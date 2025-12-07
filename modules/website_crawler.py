"""
Website Crawler Module
Crawls high-value website sections to find contact information and leadership details
"""

import re
import logging
from urllib.parse import urljoin, urlparse, urlunparse
from typing import List, Dict, Set, Optional, Tuple
from bs4 import BeautifulSoup
import requests

logger = logging.getLogger(__name__)


# Priority URL keywords for finding high-value pages
PRIORITY_PATH_KEYWORDS = [
    "contact", "about", "team", "our-team", "leadership", "our-leadership",
    "management", "staff", "people", "meet-the-team", "meet-our-team",
    "executive", "executives", "directors", "board", "founder", "founders",
    "company", "about-us", "who-we-are", "our-people", "meet-us"
]

# URL patterns to avoid (low-value pages)
AVOID_PATH_KEYWORDS = [
    "login", "signup", "register", "cart", "checkout", "account", "dashboard",
    "admin", "wp-admin", "blog", "news", "article", "post", "category",
    "tag", "search", "privacy", "terms", "cookie", "legal", "sitemap",
    "feed", "rss", "xml", "json", "api", "download", "pdf", "doc"
]


def normalize_url(url: str, base_url: str) -> str:
    """
    Normalize URL by removing fragments, converting to absolute, and cleaning.

    Args:
        url: URL to normalize
        base_url: Base URL for resolving relative URLs

    Returns:
        Normalized absolute URL
    """
    # Convert to absolute URL
    absolute_url = urljoin(base_url, url)

    # Parse URL
    parsed = urlparse(absolute_url)

    # Remove fragment and rebuild URL
    normalized = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        parsed.query,
        ''  # Remove fragment
    ))

    # Remove trailing slash for consistency
    if normalized.endswith('/') and normalized.count('/') > 3:
        normalized = normalized[:-1]

    return normalized


def is_same_domain(url: str, base_url: str) -> bool:
    """
    Check if URL belongs to the same domain as base URL.

    Args:
        url: URL to check
        base_url: Base domain URL

    Returns:
        True if same domain
    """
    try:
        url_domain = urlparse(url).netloc.lower().replace('www.', '')
        base_domain = urlparse(base_url).netloc.lower().replace('www.', '')
        return url_domain == base_domain
    except Exception:
        return False


def is_priority_url(url: str) -> bool:
    """
    Check if URL is a priority page (contact, about, team, etc.).

    Args:
        url: URL to check

    Returns:
        True if URL is high-priority
    """
    url_lower = url.lower()

    # Check if URL contains priority keywords
    has_priority = any(keyword in url_lower for keyword in PRIORITY_PATH_KEYWORDS)

    # Check if URL should be avoided
    has_avoid = any(keyword in url_lower for keyword in AVOID_PATH_KEYWORDS)

    return has_priority and not has_avoid


def extract_links_from_html(html: str, base_url: str) -> List[str]:
    """
    Extract all links from HTML content.

    Args:
        html: HTML content
        base_url: Base URL for resolving relative links

    Returns:
        List of absolute URLs
    """
    soup = BeautifulSoup(html, 'html.parser')
    links = []

    for anchor in soup.find_all('a', href=True):
        href = anchor['href'].strip()

        # Skip empty, javascript, mailto, tel links
        if not href or href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
            continue

        # Normalize URL
        try:
            absolute_url = normalize_url(href, base_url)

            # Only include same-domain links
            if is_same_domain(absolute_url, base_url):
                links.append(absolute_url)
        except Exception as e:
            logger.debug(f"Error normalizing URL {href}: {e}")

    return list(set(links))


def get_priority_urls(base_url: str, all_links: List[str]) -> List[str]:
    """
    Filter and prioritize URLs that are likely to contain valuable contact info.

    Args:
        base_url: Base website URL
        all_links: List of all discovered links

    Returns:
        List of priority URLs sorted by relevance
    """
    priority_urls = []
    url_scores = {}

    for link in all_links:
        if not is_same_domain(link, base_url):
            continue

        url_lower = link.lower()
        score = 0

        # Score based on priority keywords
        for keyword in PRIORITY_PATH_KEYWORDS:
            if keyword in url_lower:
                # Higher score for exact matches in path
                if f'/{keyword}' in url_lower or f'{keyword}/' in url_lower:
                    score += 10
                else:
                    score += 5

        # Penalize avoid keywords
        for keyword in AVOID_PATH_KEYWORDS:
            if keyword in url_lower:
                score -= 20

        # Bonus for shorter paths (likely more important pages)
        path_depth = url_lower.count('/') - 2  # Subtract protocol slashes
        score -= path_depth * 2

        if score > 0:
            priority_urls.append(link)
            url_scores[link] = score

    # Sort by score (highest first)
    priority_urls.sort(key=lambda x: url_scores.get(x, 0), reverse=True)

    return priority_urls


class PriorityWebsiteCrawler:
    """
    Crawler that prioritizes high-value website sections for contact extraction.
    """

    def __init__(self, rate_limiter=None, max_pages: int = 10):
        """
        Initialize crawler.

        Args:
            rate_limiter: RateLimitedScraper instance for fetching URLs
            max_pages: Maximum number of pages to crawl per website
        """
        self.rate_limiter = rate_limiter
        self.max_pages = max_pages
        self.visited_urls: Set[str] = set()

    def reset(self):
        """Reset crawler state for new website."""
        self.visited_urls.clear()

    def crawl_website(self, base_url: str) -> Dict:
        """
        Crawl website starting from base URL, prioritizing valuable pages.

        Args:
            base_url: Website URL to crawl

        Returns:
            Dictionary containing:
            - all_html: Combined HTML from all crawled pages
            - priority_pages: List of priority pages found
            - emails: Raw emails found
            - phones: Raw phone numbers found
        """
        self.reset()

        result = {
            'base_url': base_url,
            'crawled_pages': [],
            'priority_pages': [],
            'all_html': '',
            'emails': [],
            'phones': []
        }

        # Step 1: Fetch homepage
        logger.info(f"Crawling homepage: {base_url}")

        if self.rate_limiter:
            response = self.rate_limiter.fetch_url(base_url)
        else:
            response = requests.get(base_url, timeout=10)

        if not response or response.status_code != 200:
            logger.warning(f"Failed to fetch homepage: {base_url}")
            return result

        homepage_html = response.text
        result['all_html'] += homepage_html + '\n'
        result['crawled_pages'].append(base_url)
        self.visited_urls.add(base_url)

        # Step 2: Extract all links from homepage
        all_links = extract_links_from_html(homepage_html, base_url)
        logger.info(f"Found {len(all_links)} links on homepage")

        # Step 3: Get priority URLs
        priority_urls = get_priority_urls(base_url, all_links)
        logger.info(f"Identified {len(priority_urls)} priority URLs")

        result['priority_pages'] = priority_urls[:self.max_pages]

        # Step 4: Crawl priority pages
        pages_crawled = 1  # Already crawled homepage

        for priority_url in priority_urls:
            if pages_crawled >= self.max_pages:
                logger.info(f"Reached max pages limit ({self.max_pages})")
                break

            if priority_url in self.visited_urls:
                continue

            logger.info(f"Crawling priority page: {priority_url}")

            if self.rate_limiter:
                response = self.rate_limiter.fetch_url(priority_url)
            else:
                response = requests.get(priority_url, timeout=10)

            if response and response.status_code == 200:
                page_html = response.text
                result['all_html'] += page_html + '\n'
                result['crawled_pages'].append(priority_url)
                self.visited_urls.add(priority_url)
                pages_crawled += 1
            else:
                logger.warning(f"Failed to fetch: {priority_url}")

        logger.info(f"Crawled {pages_crawled} pages for {base_url}")

        return result


def find_mailto_links(html: str) -> List[str]:
    """
    Extract mailto: links from HTML.

    Args:
        html: HTML content

    Returns:
        List of email addresses
    """
    mailto_pattern = r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
    emails = re.findall(mailto_pattern, html, re.IGNORECASE)
    return list(set(emails))


def extract_contact_sections(html: str) -> List[str]:
    """
    Extract text from sections likely to contain contact information.

    Args:
        html: HTML content

    Returns:
        List of text content from contact sections
    """
    soup = BeautifulSoup(html, 'html.parser')
    contact_texts = []

    # Look for contact-related sections by class/id
    contact_patterns = [
        'contact', 'about', 'team', 'leadership', 'management',
        'staff', 'executive', 'founder', 'director', 'people'
    ]

    for pattern in contact_patterns:
        # Find by class
        for element in soup.find_all(class_=re.compile(pattern, re.I)):
            contact_texts.append(element.get_text(separator=' ', strip=True))

        # Find by id
        for element in soup.find_all(id=re.compile(pattern, re.I)):
            contact_texts.append(element.get_text(separator=' ', strip=True))

    return contact_texts


def extract_structured_contact_info(html: str) -> Dict:
    """
    Extract structured contact information from HTML.

    Args:
        html: HTML content

    Returns:
        Dictionary with extracted contact details
    """
    soup = BeautifulSoup(html, 'html.parser')

    result = {
        'emails': [],
        'phones': [],
        'addresses': [],
        'social_links': []
    }

    # Extract mailto links
    result['emails'].extend(find_mailto_links(html))

    # Extract tel links
    for tel_link in soup.find_all('a', href=re.compile(r'^tel:', re.I)):
        phone = tel_link['href'].replace('tel:', '').strip()
        result['phones'].append(phone)

    # Extract social media links
    social_domains = ['linkedin.com', 'facebook.com', 'twitter.com', 'instagram.com']
    for link in soup.find_all('a', href=True):
        href = link['href'].lower()
        if any(domain in href for domain in social_domains):
            result['social_links'].append(link['href'])

    return result

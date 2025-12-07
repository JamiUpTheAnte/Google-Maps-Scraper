"""
Google Maps Scraper using Selenium
Opens Chrome browser and scrapes Google Maps business listings
"""

import time
import logging
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import random

logger = logging.getLogger(__name__)


class GoogleMapsScraper:
    """
    Scraper that uses Selenium to open Chrome and scrape Google Maps listings
    """

    def __init__(self, headless=False):
        """
        Initialize Google Maps scraper.

        Args:
            headless: Run Chrome in headless mode (no visible window)
        """
        self.headless = headless
        self.driver = None

    def init_driver(self):
        """Initialize Chrome WebDriver"""
        try:
            chrome_options = Options()

            if self.headless:
                chrome_options.add_argument('--headless')

            # Recommended Chrome options
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

            # Disable automation flags
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            # Use Selenium Manager (built into Selenium 4.6+)
            # It automatically downloads the correct ChromeDriver for your system
            # No need for webdriver-manager!
            self.driver = webdriver.Chrome(options=chrome_options)

            # Remove webdriver property
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            logger.info("✓ Chrome WebDriver initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Chrome WebDriver: {e}")
            return False

    def close_driver(self):
        """Close Chrome WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Chrome WebDriver closed")
            except Exception as e:
                logger.error(f"Error closing driver: {e}")

    def search_google_maps(self, query: str, location: str, max_results: int = 50) -> List[Dict]:
        """
        Search Google Maps and extract business listings.

        Args:
            query: Business type (e.g., "construction company")
            location: Location (e.g., "Atlanta")
            max_results: Maximum number of results to scrape

        Returns:
            List of business dictionaries with name, website, phone, etc.
        """
        if not self.driver:
            if not self.init_driver():
                return []

        businesses = []

        try:
            # Construct search query
            search_query = f"{query} {location}"
            logger.info(f"Searching Google Maps for: '{search_query}'")

            # Navigate to Google Maps
            self.driver.get("https://www.google.com/maps")
            time.sleep(2)

            # Find search box and enter query
            search_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "searchboxinput"))
            )
            search_box.clear()
            search_box.send_keys(search_query)
            search_box.send_keys(Keys.ENTER)

            logger.info("Search submitted, waiting for results...")
            time.sleep(5)  # Wait for results to load

            # Scroll through results to load more
            results_container = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='feed']"))
            )

            logger.info("Scrolling to load more results...")

            # Scroll multiple times to load more results
            for scroll in range(10):  # Adjust scroll count as needed
                self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", results_container)
                time.sleep(random.uniform(1, 2))

                # Check if we've loaded enough
                current_results = len(self.driver.find_elements(By.CSS_SELECTOR, "div[role='feed'] > div > div > a"))
                logger.info(f"Loaded {current_results} results so far...")

                if current_results >= max_results:
                    break

            # Extract business listings
            logger.info("Extracting business information...")
            business_links = self.driver.find_elements(By.CSS_SELECTOR, "div[role='feed'] > div > div > a")

            for i, link in enumerate(business_links[:max_results], 1):
                try:
                    logger.info(f"Processing business {i}/{min(len(business_links), max_results)}...")

                    # Click on the business listing
                    self.driver.execute_script("arguments[0].click();", link)
                    time.sleep(random.uniform(2, 3))

                    business = self.extract_business_details()

                    if business:
                        businesses.append(business)
                        logger.info(f"✓ Extracted: {business['name']}")

                except Exception as e:
                    logger.warning(f"Error extracting business {i}: {e}")
                    continue

            logger.info(f"✓ Extracted {len(businesses)} businesses from Google Maps")

        except TimeoutException:
            logger.error("Timeout waiting for Google Maps elements")
        except Exception as e:
            logger.error(f"Error scraping Google Maps: {e}")

        return businesses

    def extract_business_details(self) -> Optional[Dict]:
        """
        Extract details from currently open business listing.

        Returns:
            Dictionary with business information
        """
        business = {
            'name': '',
            'website': '',
            'phone': '',
            'address': '',
            'rating': '',
            'reviews': '',
            'category': '',
            'source': 'google_maps'
        }

        try:
            # Extract business name
            try:
                name_elem = self.driver.find_element(By.CSS_SELECTOR, "h1.DUwDvf")
                business['name'] = name_elem.text.strip()
            except NoSuchElementException:
                logger.warning("Could not find business name")

            # Extract website
            try:
                website_elem = self.driver.find_element(By.CSS_SELECTOR, "a[data-item-id='authority']")
                business['website'] = website_elem.get_attribute('href')
            except NoSuchElementException:
                logger.debug("No website found for this business")

            # Extract phone
            try:
                phone_elem = self.driver.find_element(By.CSS_SELECTOR, "button[data-item-id^='phone:tel:']")
                business['phone'] = phone_elem.get_attribute('data-item-id').replace('phone:tel:', '')
            except NoSuchElementException:
                logger.debug("No phone found for this business")

            # Extract address
            try:
                address_elem = self.driver.find_element(By.CSS_SELECTOR, "button[data-item-id='address']")
                business['address'] = address_elem.get_attribute('aria-label').replace('Address: ', '')
            except NoSuchElementException:
                logger.debug("No address found for this business")

            # Extract rating
            try:
                rating_elem = self.driver.find_element(By.CSS_SELECTOR, "div.F7nice span[aria-hidden='true']")
                business['rating'] = rating_elem.text.strip()
            except NoSuchElementException:
                logger.debug("No rating found for this business")

            # Extract review count
            try:
                reviews_elem = self.driver.find_element(By.CSS_SELECTOR, "div.F7nice span[aria-label*='reviews']")
                business['reviews'] = reviews_elem.get_attribute('aria-label')
            except NoSuchElementException:
                logger.debug("No reviews found for this business")

            # Extract category
            try:
                category_elem = self.driver.find_element(By.CSS_SELECTOR, "button.DkEaL")
                business['category'] = category_elem.text.strip()
            except NoSuchElementException:
                logger.debug("No category found for this business")

            return business if business['name'] else None

        except Exception as e:
            logger.error(f"Error extracting business details: {e}")
            return None


def search_google_maps(query: str, location: str = "", num_results: int = 50,
                       headless: bool = False) -> List[Dict]:
    """
    Convenience function to search Google Maps.

    Args:
        query: Business type
        location: Location
        num_results: Max number of results
        headless: Run Chrome in headless mode

    Returns:
        List of business dictionaries
    """
    scraper = GoogleMapsScraper(headless=headless)

    try:
        businesses = scraper.search_google_maps(query, location, num_results)
        return businesses
    finally:
        scraper.close_driver()

"""
Email Verification and Pattern Generation Module
Generates email patterns from names and verifies them using MailboxLayer API
"""

import re
import time
import logging
import requests
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class EmailPatternGenerator:
    """
    Generates probable email patterns from first and last names.
    """

    @staticmethod
    def clean_name(name: str) -> str:
        """
        Clean and normalize name for email generation.

        Args:
            name: Name to clean

        Returns:
            Cleaned name (lowercase, no special chars)
        """
        if not name:
            return ""

        # Convert to lowercase
        name = name.lower().strip()

        # Remove accents and special characters
        name = re.sub(r'[^a-z]', '', name)

        return name

    @staticmethod
    def generate_patterns(first: str, last: str, domain: str) -> List[str]:
        """
        Generate probable email patterns from first/last name and domain.

        Args:
            first: First name
            last: Last name
            domain: Email domain

        Returns:
            List of email patterns sorted by probability
        """
        # Clean inputs
        first = EmailPatternGenerator.clean_name(first)
        last = EmailPatternGenerator.clean_name(last)
        domain = domain.lower().strip()

        if not domain:
            return []

        patterns = []

        # Most common patterns (in order of likelihood)
        if first and last:
            patterns.extend([
                f"{first}.{last}@{domain}",        # john.doe@company.com (most common)
                f"{first}{last}@{domain}",          # johndoe@company.com
                f"{first[0]}{last}@{domain}",      # jdoe@company.com
                f"{first}_{last}@{domain}",        # john_doe@company.com
                f"{last}.{first}@{domain}",        # doe.john@company.com
                f"{first[0]}.{last}@{domain}",     # j.doe@company.com
                f"{first}{last[0]}@{domain}",      # johnd@company.com
                f"{last}@{domain}",                # doe@company.com
            ])
        elif first:
            patterns.extend([
                f"{first}@{domain}",               # john@company.com
            ])
        elif last:
            patterns.extend([
                f"{last}@{domain}",                # doe@company.com
            ])

        # Remove duplicates while preserving order
        seen = set()
        unique_patterns = []
        for pattern in patterns:
            if pattern not in seen and len(pattern) > 0:
                seen.add(pattern)
                unique_patterns.append(pattern)

        return unique_patterns

    @staticmethod
    def generate_from_name_dict(name_dict: Dict, domain: str) -> List[str]:
        """
        Generate patterns from name dictionary.

        Args:
            name_dict: Dictionary with 'first_name' and 'last_name' keys
            domain: Email domain

        Returns:
            List of email patterns
        """
        first = name_dict.get('first_name', '')
        last = name_dict.get('last_name', '')
        return EmailPatternGenerator.generate_patterns(first, last, domain)


class MailboxLayerVerifier:
    """
    Email verification using MailboxLayer API.
    """

    def __init__(self, api_key: str, rate_limit_delay: float = 1.0):
        """
        Initialize verifier.

        Args:
            api_key: MailboxLayer API key
            rate_limit_delay: Delay between API calls (seconds)
        """
        self.api_key = api_key
        self.rate_limit_delay = rate_limit_delay
        self.last_request_time = 0
        self.base_url = "https://apilayer.net/api/check"

    def _apply_rate_limit(self):
        """Apply rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def verify_email(self, email: str, timeout: int = 10) -> Tuple[bool, Dict]:
        """
        Verify email address using MailboxLayer API.

        Args:
            email: Email address to verify
            timeout: Request timeout in seconds

        Returns:
            Tuple of (is_valid, metadata_dict)
        """
        self._apply_rate_limit()

        try:
            response = requests.get(
                self.base_url,
                params={
                    'access_key': self.api_key,
                    'email': email,
                    'smtp': 1,  # Enable SMTP check
                    'format': 1  # Return formatted response
                },
                timeout=timeout
            )

            if response.status_code != 200:
                logger.warning(f"MailboxLayer API returned status {response.status_code}")
                return False, {'error': f'API returned {response.status_code}'}

            data = response.json()

            # Check for API errors
            if 'error' in data:
                logger.warning(f"MailboxLayer API error: {data['error']}")
                return False, data

            # Determine if email is valid based on MailboxLayer response
            is_valid = (
                data.get('format_valid', False)           # Format is valid
                and data.get('mx_found', False)           # MX records exist
                and not data.get('disposable', False)     # Not a disposable email
                and data.get('score', 0) >= 0.45          # Quality score >= 0.45
            )

            # Additional check: SMTP validation if available
            if data.get('smtp_check', False):
                is_valid = is_valid and not data.get('catch_all', False)

            logger.info(f"Verified {email}: {'valid' if is_valid else 'invalid'} (score: {data.get('score', 0)})")

            return is_valid, data

        except requests.exceptions.Timeout:
            logger.error(f"Timeout verifying email: {email}")
            return False, {'error': 'timeout'}

        except requests.exceptions.RequestException as e:
            logger.error(f"Error verifying email {email}: {e}")
            return False, {'error': str(e)}

        except Exception as e:
            logger.error(f"Unexpected error verifying {email}: {e}")
            return False, {'error': str(e)}

    def verify_patterns(self, patterns: List[str], max_attempts: int = 5) -> Optional[Dict]:
        """
        Verify email patterns until a valid one is found.

        Args:
            patterns: List of email patterns to try
            max_attempts: Maximum number of patterns to verify

        Returns:
            Dictionary with best email and metadata, or None
        """
        for i, pattern in enumerate(patterns[:max_attempts]):
            logger.info(f"Verifying pattern {i+1}/{min(len(patterns), max_attempts)}: {pattern}")

            is_valid, metadata = self.verify_email(pattern)

            if is_valid:
                return {
                    'email': pattern,
                    'verified': True,
                    'metadata': metadata,
                    'pattern_index': i
                }

        logger.info(f"No valid email found in {min(len(patterns), max_attempts)} patterns")
        return None


class EmailEnricher:
    """
    Combines pattern generation and verification to find decision-maker emails.
    """

    def __init__(self, mailbox_verifier: Optional[MailboxLayerVerifier] = None):
        """
        Initialize enricher.

        Args:
            mailbox_verifier: MailboxLayerVerifier instance (optional)
        """
        self.verifier = mailbox_verifier
        self.pattern_gen = EmailPatternGenerator()

    def extract_domain_from_url(self, url: str) -> Optional[str]:
        """
        Extract email domain from website URL.

        Args:
            url: Website URL

        Returns:
            Email domain or None
        """
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname or parsed.path

            if not hostname:
                return None

            # Remove www. prefix
            domain = hostname.replace('www.', '').lower()

            return domain

        except Exception as e:
            logger.warning(f"Error extracting domain from {url}: {e}")
            return None

    def enrich_leadership_with_emails(self, leadership_names: List[Dict],
                                     website_url: str,
                                     verify: bool = True,
                                     max_per_person: int = 3) -> List[Dict]:
        """
        Enrich leadership names with generated and verified email addresses.

        Args:
            leadership_names: List of leadership name dictionaries
            website_url: Company website URL
            verify: Whether to verify emails with MailboxLayer
            max_per_person: Maximum email patterns to try per person

        Returns:
            List of enriched leadership records with emails
        """
        domain = self.extract_domain_from_url(website_url)

        if not domain:
            logger.warning(f"Could not extract domain from {website_url}")
            return leadership_names

        enriched = []

        for person in leadership_names:
            first = person.get('first_name', '')
            last = person.get('last_name', '')

            # Generate email patterns
            patterns = self.pattern_gen.generate_patterns(first, last, domain)

            if not patterns:
                logger.warning(f"No patterns generated for {first} {last}")
                enriched.append(person)
                continue

            person_copy = person.copy()
            person_copy['email_patterns'] = patterns

            # Verify patterns if verifier is available
            if verify and self.verifier:
                result = self.verifier.verify_patterns(patterns, max_attempts=max_per_person)

                if result:
                    person_copy['email'] = result['email']
                    person_copy['email_verified'] = True
                    person_copy['email_metadata'] = result['metadata']
                    logger.info(f"✓ Found verified email for {first} {last}: {result['email']}")
                else:
                    person_copy['email'] = patterns[0]  # Best guess
                    person_copy['email_verified'] = False
                    logger.info(f"✗ No verified email found for {first} {last}, using best guess: {patterns[0]}")
            else:
                # No verification, use best pattern
                person_copy['email'] = patterns[0]
                person_copy['email_verified'] = False

            enriched.append(person_copy)

        return enriched

    def find_decision_maker_email(self, first: str, last: str, website_url: str,
                                 verify: bool = True) -> Optional[str]:
        """
        Find and verify email for a single decision-maker.

        Args:
            first: First name
            last: Last name
            website_url: Company website
            verify: Whether to verify with MailboxLayer

        Returns:
            Verified email address or None
        """
        domain = self.extract_domain_from_url(website_url)

        if not domain:
            return None

        patterns = self.pattern_gen.generate_patterns(first, last, domain)

        if not patterns:
            return None

        if verify and self.verifier:
            result = self.verifier.verify_patterns(patterns)
            return result['email'] if result else None
        else:
            return patterns[0]  # Return best guess


# Convenience functions for direct use
def generate_email_patterns(first: str, last: str, domain: str) -> List[str]:
    """
    Generate email patterns (convenience function).

    Args:
        first: First name
        last: Last name
        domain: Email domain

    Returns:
        List of email patterns
    """
    return EmailPatternGenerator.generate_patterns(first, last, domain)


def verify_email_mailboxlayer(email: str, api_key: str) -> Tuple[bool, Dict]:
    """
    Verify email with MailboxLayer (convenience function).

    Args:
        email: Email to verify
        api_key: MailboxLayer API key

    Returns:
        Tuple of (is_valid, metadata)
    """
    verifier = MailboxLayerVerifier(api_key)
    return verifier.verify_email(email)

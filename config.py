"""
Configuration Management
Centralized configuration for the scraper
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration"""

    # API Keys
    MAILBOXLAYER_API_KEY = os.getenv('MAILBOXLAYER_API_KEY', '')

    # Scraper Settings
    ENABLE_ENRICHMENT = os.getenv('ENABLE_ENRICHMENT', 'false').lower() == 'true'
    MIN_DELAY = float(os.getenv('MIN_DELAY', '3.0'))
    MAX_DELAY = float(os.getenv('MAX_DELAY', '7.0'))
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '10'))

    # Enrichment Settings
    MAX_PAGES_PER_SITE = int(os.getenv('MAX_PAGES_PER_SITE', '10'))
    MAX_DECISION_MAKERS = int(os.getenv('MAX_DECISION_MAKERS', '5'))
    EMAIL_MIN_QUALITY_SCORE = int(os.getenv('EMAIL_MIN_QUALITY_SCORE', '50'))

    # Flask Settings
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    FLASK_PORT = int(os.getenv('FLASK_PORT', '5000'))

    # Google Search Settings
    DEFAULT_NUM_RESULTS = int(os.getenv('DEFAULT_NUM_RESULTS', '50'))
    SEARCH_LANGUAGE = os.getenv('SEARCH_LANGUAGE', 'en')

    @classmethod
    def validate(cls):
        """Validate configuration"""
        errors = []

        if cls.ENABLE_ENRICHMENT and not cls.MAILBOXLAYER_API_KEY:
            errors.append(
                "MAILBOXLAYER_API_KEY is required when ENABLE_ENRICHMENT is true"
            )

        if cls.MIN_DELAY < 0 or cls.MAX_DELAY < cls.MIN_DELAY:
            errors.append("Invalid delay settings: MAX_DELAY must be >= MIN_DELAY >= 0")

        if errors:
            raise ValueError("Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))

        return True

    @classmethod
    def get_scraper_config(cls):
        """Get configuration dict for scraper initialization"""
        return {
            'min_delay': cls.MIN_DELAY,
            'max_delay': cls.MAX_DELAY,
            'request_timeout': cls.REQUEST_TIMEOUT,
            'enable_enrichment': cls.ENABLE_ENRICHMENT,
            'mailbox_api_key': cls.MAILBOXLAYER_API_KEY
        }

    @classmethod
    def print_config(cls):
        """Print current configuration (for debugging)"""
        print("=" * 60)
        print("Google Maps Scraper Configuration")
        print("=" * 60)
        print(f"Enrichment enabled: {cls.ENABLE_ENRICHMENT}")
        print(f"MailboxLayer API configured: {'Yes' if cls.MAILBOXLAYER_API_KEY else 'No'}")
        print(f"Rate limiting: {cls.MIN_DELAY}-{cls.MAX_DELAY}s")
        print(f"Max pages per site: {cls.MAX_PAGES_PER_SITE}")
        print(f"Max decision makers: {cls.MAX_DECISION_MAKERS}")
        print("=" * 60)

"""
Email Quality Filtering Module
Filters out junk emails and prioritizes high-value contacts
"""

import re
from urllib.parse import urlparse
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


# Email classification constants
BAD_LOCAL_PARTS = {
    "wordpress", "no-reply", "noreply", "postmaster", "webmaster",
    "administrator", "admin", "hostmaster", "mailer-daemon", "abuse",
    "root", "daemon", "bin", "sys", "adm", "nobody", "www", "data",
    "ftp", "mail", "bounce", "bounces", "unsubscribe", "donotreply",
    "do-not-reply", "automated", "automatic", "robot", "notification",
    "notifications", "alert", "alerts", "system", "privacy", "legal",
    "compliance", "security", "spam", "test", "demo"
}

LOW_PRIORITY_PARTS = {
    "info", "contact", "office", "support", "sales", "help",
    "service", "customer", "customerservice", "generalinfo",
    "inquiry", "inquiries", "reception", "general", "hello",
    "hi", "team", "mail", "email", "accounts", "billing",
    "feedback", "questions", "hr", "careers", "jobs", "recruiting"
}

# Domains to filter out (free email providers and common spam domains)
BLACKLIST_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com",
    "live.com", "msn.com", "icloud.com", "mail.com", "protonmail.com",
    "zoho.com", "yandex.com", "gmx.com", "me.com", "inbox.com",
    "example.com", "test.com", "sample.com", "domain.com", "email.com",
    "tempmail.com", "guerrillamail.com", "mailinator.com", "10minutemail.com",
    "trashmail.com", "throwaway.email", "sharklasers.com"
}

# Common business domain extensions that indicate legitimate company emails
BUSINESS_DOMAIN_EXTENSIONS = {
    ".com", ".co", ".net", ".org", ".io", ".ai", ".tech", ".biz",
    ".pro", ".inc", ".llc", ".corp", ".company", ".construction",
    ".contractors", ".services", ".solutions", ".group", ".partners"
}


def extract_email_parts(email: str) -> Tuple[str, str]:
    """
    Extract local part and domain from email address.

    Args:
        email: Email address

    Returns:
        Tuple of (local_part, domain)
    """
    try:
        local, domain = email.lower().strip().split('@', 1)
        return local, domain
    except ValueError:
        logger.warning(f"Invalid email format: {email}")
        return "", ""


def is_company_domain(email: str, website_url: str) -> bool:
    """
    Check if email belongs to the company's domain.

    Args:
        email: Email address to check
        website_url: Company website URL

    Returns:
        True if email domain matches company domain
    """
    if not email or not website_url:
        return False

    try:
        _, email_domain = extract_email_parts(email)

        # Parse website URL to get domain
        parsed = urlparse(website_url)
        website_host = parsed.hostname or parsed.path

        if not website_host:
            return False

        # Remove www. prefix
        website_domain = website_host.replace('www.', '').lower()

        # Check if email domain matches or is a subdomain of website domain
        return email_domain == website_domain or email_domain.endswith('.' + website_domain)

    except Exception as e:
        logger.warning(f"Error checking company domain for {email}: {e}")
        return False


def is_blacklisted_domain(email: str) -> bool:
    """
    Check if email uses a blacklisted domain (free providers, temp emails).

    Args:
        email: Email address to check

    Returns:
        True if domain is blacklisted
    """
    _, domain = extract_email_parts(email)
    return domain in BLACKLIST_DOMAINS


def is_valid_email_format(email: str) -> bool:
    """
    Validate email format using regex.

    Args:
        email: Email address to validate

    Returns:
        True if email format is valid
    """
    pattern = r'^[a-zA-Z0-9][a-zA-Z0-9._%+-]*@[a-zA-Z0-9][a-zA-Z0-9.-]*\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def classify_email(email: str) -> str:
    """
    Classify email into categories based on local part.

    Categories:
    - dev_junk: Development/system emails to exclude
    - role_generic: Generic role-based emails (low priority)
    - person_or_good: Likely person-specific or good quality email

    Args:
        email: Email address to classify

    Returns:
        Classification category
    """
    local, _ = extract_email_parts(email)

    if not local:
        return "dev_junk"

    # Remove dots and hyphens for matching
    local_clean = local.replace('.', '').replace('-', '').replace('_', '')

    # Check for dev/junk patterns
    if local_clean in BAD_LOCAL_PARTS or local in BAD_LOCAL_PARTS:
        return "dev_junk"

    # Check for partial matches in bad local parts
    for bad_part in BAD_LOCAL_PARTS:
        if bad_part in local_clean or bad_part in local:
            return "dev_junk"

    # Check for low priority role emails
    if local_clean in LOW_PRIORITY_PARTS or local in LOW_PRIORITY_PARTS:
        return "role_generic"

    # Check for partial matches in low priority
    for low_part in LOW_PRIORITY_PARTS:
        if local.startswith(low_part) or local.endswith(low_part):
            return "role_generic"

    # Likely a person-specific or good quality email
    return "person_or_good"


def score_email_quality(email: str, website_url: Optional[str] = None) -> Dict:
    """
    Score email quality with detailed metrics.

    Args:
        email: Email address to score
        website_url: Company website URL (optional)

    Returns:
        Dictionary with quality score and details
    """
    score = 100  # Start with perfect score
    reasons = []

    # Format validation
    if not is_valid_email_format(email):
        score -= 100
        reasons.append("Invalid email format")
        return {
            'email': email,
            'score': 0,
            'classification': 'invalid',
            'is_company_domain': False,
            'is_blacklisted': False,
            'reasons': reasons,
            'accept': False
        }

    # Classify email
    classification = classify_email(email)

    # Check blacklist
    is_blacklisted = is_blacklisted_domain(email)

    # Check company domain
    is_company = is_company_domain(email, website_url) if website_url else False

    # Apply scoring rules
    if classification == "dev_junk":
        score -= 100
        reasons.append("Development/system email")
    elif classification == "role_generic":
        score -= 40
        reasons.append("Generic role-based email")

    if is_blacklisted:
        score -= 80
        reasons.append("Blacklisted domain (free provider or temp email)")

    if website_url and not is_company:
        score -= 50
        reasons.append("Not from company domain")
    elif is_company:
        score += 20
        reasons.append("Company domain match")

    # Check for common name patterns (indicates person-specific)
    local, _ = extract_email_parts(email)
    if '.' in local and len(local.split('.')) == 2:
        # Likely firstname.lastname pattern
        score += 15
        reasons.append("Possible firstname.lastname pattern")

    # Determine if email should be accepted
    accept = score >= 50 and classification != "dev_junk"

    return {
        'email': email,
        'score': max(0, score),
        'classification': classification,
        'is_company_domain': is_company,
        'is_blacklisted': is_blacklisted,
        'reasons': reasons,
        'accept': accept
    }


def filter_emails(emails: List[str], website_url: Optional[str] = None,
                 min_score: int = 50, exclude_generic: bool = False) -> List[Dict]:
    """
    Filter and rank emails by quality.

    Args:
        emails: List of email addresses to filter
        website_url: Company website URL for domain matching
        min_score: Minimum quality score to accept (0-100)
        exclude_generic: If True, exclude role_generic emails

    Returns:
        List of accepted emails with quality metadata, sorted by score
    """
    results = []

    for email in emails:
        quality = score_email_quality(email, website_url)

        # Apply filters
        if quality['score'] < min_score:
            continue

        if exclude_generic and quality['classification'] == 'role_generic':
            continue

        if quality['accept']:
            results.append(quality)

    # Sort by score (highest first)
    results.sort(key=lambda x: x['score'], reverse=True)

    return results


def get_best_emails(emails: List[str], website_url: Optional[str] = None,
                   limit: int = 5) -> List[str]:
    """
    Get the best quality emails from a list.

    Args:
        emails: List of email addresses
        website_url: Company website URL
        limit: Maximum number of emails to return

    Returns:
        List of best quality email addresses
    """
    filtered = filter_emails(emails, website_url, min_score=60)
    return [item['email'] for item in filtered[:limit]]


def extract_mailto_links(html: str) -> List[str]:
    """
    Extract email addresses from mailto: links in HTML.

    Args:
        html: HTML content

    Returns:
        List of email addresses
    """
    mailto_pattern = r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
    emails = re.findall(mailto_pattern, html, re.IGNORECASE)
    return list(set(emails))


def extract_emails_from_text(text: str) -> List[str]:
    """
    Extract email addresses from plain text.

    Args:
        text: Text content

    Returns:
        List of email addresses
    """
    email_pattern = r'\b[a-zA-Z0-9][a-zA-Z0-9._%+-]*@[a-zA-Z0-9][a-zA-Z0-9.-]*\.[a-zA-Z]{2,}\b'
    emails = re.findall(email_pattern, text)

    # Filter out common false positives
    filtered = [
        email for email in emails
        if not any(exclude in email.lower() for exclude in [
            'example.com', 'samplesite', 'yoursite', 'yourdomain',
            'domain.com', 'email.com', 'image.', '.png', '.jpg', '.gif'
        ])
    ]

    return list(set(filtered))


# Convenience function for backward compatibility
def extract_emails(text: str) -> List[str]:
    """
    Extract all emails from text (combines mailto and plain text extraction).

    Args:
        text: Text or HTML content

    Returns:
        List of unique email addresses
    """
    mailto_emails = extract_mailto_links(text)
    text_emails = extract_emails_from_text(text)

    all_emails = set(mailto_emails + text_emails)
    return list(all_emails)

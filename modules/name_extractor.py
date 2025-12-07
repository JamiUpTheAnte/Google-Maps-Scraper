"""
Leadership Name Extraction Module
Extracts names of decision-makers and leadership from website content
"""

import re
import logging
from typing import List, Dict, Set, Tuple, Optional
from bs4 import BeautifulSoup
from collections import defaultdict

logger = logging.getLogger(__name__)


# Leadership titles and roles
LEADERSHIP_TITLES = {
    # C-level
    'ceo', 'chief executive officer', 'chief executive',
    'cto', 'chief technology officer', 'chief technical officer',
    'cfo', 'chief financial officer',
    'coo', 'chief operating officer',
    'cmo', 'chief marketing officer',
    'cio', 'chief information officer',
    'cso', 'chief security officer',
    'cdo', 'chief data officer',
    'cpo', 'chief product officer',

    # President/VP
    'president', 'vice president', 'vp', 'v.p.',
    'executive vp', 'executive vice president', 'evp',
    'senior vp', 'senior vice president', 'svp',

    # Director level
    'director', 'managing director', 'executive director',
    'senior director', 'director of',

    # Founder/Owner
    'founder', 'co-founder', 'owner', 'co-owner',
    'principal', 'managing principal', 'partner',
    'managing partner', 'senior partner',

    # Manager
    'manager', 'general manager', 'senior manager',
    'head of', 'department head', 'team lead',

    # Specific roles
    'project manager', 'operations manager', 'sales manager',
    'business development manager', 'account manager'
}

# Words that indicate a name is likely present
NAME_INDICATORS = {
    'founded by', 'led by', 'managed by', 'run by', 'owned by',
    'meet', 'contact', 'reach out to', 'speak with', 'talk to'
}


def is_valid_name(first: str, last: str = None) -> bool:
    """
    Check if extracted name components are valid.

    Args:
        first: First name
        last: Last name (optional)

    Returns:
        True if name appears valid
    """
    if not first or len(first) < 2:
        return False

    # Check for common false positives
    invalid_patterns = [
        'phone', 'email', 'address', 'contact', 'info', 'office',
        'company', 'business', 'inc', 'llc', 'corp', 'ltd',
        'http', 'www', 'lorem', 'ipsum', 'example', 'test'
    ]

    first_lower = first.lower()
    if any(pattern in first_lower for pattern in invalid_patterns):
        return False

    if last:
        last_lower = last.lower()
        if any(pattern in last_lower for pattern in invalid_patterns):
            return False

    # Name should start with capital letter
    if not first[0].isupper():
        return False

    # Name should be mostly alphabetic
    alpha_ratio = sum(c.isalpha() for c in first) / len(first)
    if alpha_ratio < 0.7:
        return False

    return True


def extract_name_from_text(text: str) -> Optional[Tuple[str, str]]:
    """
    Extract first and last name from text using pattern matching.

    Args:
        text: Text containing potential name

    Returns:
        Tuple of (first_name, last_name) or None
    """
    # Pattern: Capitalized First Last (most common)
    pattern1 = r'\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b'

    # Pattern: First Middle Last
    pattern2 = r'\b([A-Z][a-z]+)\s+(?:[A-Z][a-z]+\s+)?([A-Z][a-z]+)\b'

    # Try pattern 1 first
    match = re.search(pattern1, text)
    if match:
        first, last = match.groups()
        if is_valid_name(first, last):
            return (first, last)

    # Try pattern 2
    match = re.search(pattern2, text)
    if match:
        first, last = match.groups()
        if is_valid_name(first, last):
            return (first, last)

    return None


def extract_names_with_titles(text: str) -> List[Dict]:
    """
    Extract names along with their titles from text.

    Args:
        text: Text content to analyze

    Returns:
        List of dictionaries with name and title information
    """
    results = []
    seen_names = set()

    # Clean text
    text = re.sub(r'\s+', ' ', text)

    # Look for patterns: "Title: Name" or "Name, Title"
    for title in LEADERSHIP_TITLES:
        # Pattern: "Title: First Last" or "Title - First Last"
        pattern1 = rf'{re.escape(title)}[\s:,-]+([A-Z][a-z]+\s+[A-Z][a-z]+)'

        # Pattern: "First Last, Title" or "First Last - Title"
        pattern2 = rf'([A-Z][a-z]+\s+[A-Z][a-z]+)[\s,.-]+{re.escape(title)}'

        for pattern in [pattern1, pattern2]:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                name = match.group(1).strip()
                name_tuple = extract_name_from_text(name)

                if name_tuple and name_tuple not in seen_names:
                    first, last = name_tuple
                    results.append({
                        'first_name': first,
                        'last_name': last,
                        'full_name': f"{first} {last}",
                        'title': title,
                        'confidence': 'high'
                    })
                    seen_names.add(name_tuple)

    return results


def extract_names_from_structured_html(html: str) -> List[Dict]:
    """
    Extract names from structured HTML sections (team pages, bios, etc.).

    Args:
        html: HTML content

    Returns:
        List of dictionaries with name information
    """
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    seen_names = set()

    # Look for team/leadership sections
    team_sections = []

    # Find by class/id
    patterns = ['team', 'leadership', 'staff', 'management', 'about', 'executive', 'founder', 'director']

    for pattern in patterns:
        team_sections.extend(soup.find_all(class_=re.compile(pattern, re.I)))
        team_sections.extend(soup.find_all(id=re.compile(pattern, re.I)))

    # Also check for specific HTML5 elements
    team_sections.extend(soup.find_all(['section', 'article', 'div'], attrs={'data-section': re.compile('team|leadership|staff', re.I)}))

    for section in team_sections:
        text = section.get_text(separator=' ', strip=True)

        # Extract names with titles from this section
        names = extract_names_with_titles(text)

        for name in names:
            name_tuple = (name['first_name'], name['last_name'])
            if name_tuple not in seen_names:
                results.append(name)
                seen_names.add(name_tuple)

        # Also try to find structured person cards (common in team pages)
        person_cards = section.find_all(['div', 'li', 'article'], class_=re.compile('person|member|staff|team-member|bio', re.I))

        for card in person_cards:
            card_text = card.get_text(separator=' ', strip=True)

            # Look for name and title in card
            name_tuple = extract_name_from_text(card_text)

            if name_tuple and name_tuple not in seen_names:
                first, last = name_tuple

                # Try to find title in the same card
                title = None
                for leadership_title in LEADERSHIP_TITLES:
                    if leadership_title in card_text.lower():
                        title = leadership_title
                        break

                results.append({
                    'first_name': first,
                    'last_name': last,
                    'full_name': f"{first} {last}",
                    'title': title or 'unknown',
                    'confidence': 'medium'
                })
                seen_names.add(name_tuple)

    return results


def extract_names_from_contact_info(text: str) -> List[Dict]:
    """
    Extract names from contact information sections.

    Args:
        text: Contact section text

    Returns:
        List of dictionaries with name information
    """
    results = []
    seen_names = set()

    # Look for patterns like "Contact John Doe" or "Reach out to Jane Smith"
    for indicator in NAME_INDICATORS:
        pattern = rf'{re.escape(indicator)}\s+([A-Z][a-z]+\s+[A-Z][a-z]+)'
        matches = re.finditer(pattern, text, re.IGNORECASE)

        for match in matches:
            name = match.group(1).strip()
            name_tuple = extract_name_from_text(name)

            if name_tuple and name_tuple not in seen_names:
                first, last = name_tuple
                results.append({
                    'first_name': first,
                    'last_name': last,
                    'full_name': f"{first} {last}",
                    'title': 'contact',
                    'confidence': 'low'
                })
                seen_names.add(name_tuple)

    return results


def score_leadership_names(names: List[Dict]) -> List[Dict]:
    """
    Score and rank extracted names by leadership priority.

    Args:
        names: List of name dictionaries

    Returns:
        List of names sorted by relevance score
    """
    # Define scoring weights
    title_scores = {
        'ceo': 100, 'chief executive officer': 100,
        'president': 90, 'founder': 90, 'owner': 85,
        'cto': 80, 'cfo': 80, 'coo': 80, 'cmo': 75,
        'managing director': 70, 'director': 60,
        'vice president': 60, 'vp': 60,
        'manager': 40, 'head of': 40,
        'partner': 50, 'principal': 50,
        'contact': 20, 'unknown': 10
    }

    confidence_scores = {
        'high': 30,
        'medium': 20,
        'low': 10
    }

    for name in names:
        score = 0

        # Score by title
        title = name.get('title', '').lower()
        for title_key, title_score in title_scores.items():
            if title_key in title:
                score += title_score
                break

        # Score by confidence
        confidence = name.get('confidence', 'low')
        score += confidence_scores.get(confidence, 0)

        name['score'] = score

    # Sort by score (highest first)
    names.sort(key=lambda x: x.get('score', 0), reverse=True)

    return names


def extract_leadership_names(html: str, text: str = None) -> List[Dict]:
    """
    Main function to extract leadership names from website content.

    Args:
        html: HTML content
        text: Optional plain text content

    Returns:
        List of leadership names sorted by relevance
    """
    all_names = []

    # Extract from structured HTML
    structured_names = extract_names_from_structured_html(html)
    all_names.extend(structured_names)

    # Extract from plain text with titles
    if text:
        text_names = extract_names_with_titles(text)
        all_names.extend(text_names)
    else:
        # Extract text from HTML if not provided
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)
        text_names = extract_names_with_titles(text)
        all_names.extend(text_names)

    # Extract from contact sections
    contact_names = extract_names_from_contact_info(text or html)
    all_names.extend(contact_names)

    # Remove duplicates based on full name
    unique_names = {}
    for name in all_names:
        full_name = name['full_name']
        if full_name not in unique_names:
            unique_names[full_name] = name
        else:
            # Keep the one with higher confidence or better title
            existing = unique_names[full_name]
            if name.get('confidence') == 'high' and existing.get('confidence') != 'high':
                unique_names[full_name] = name
            elif name.get('title') in ['ceo', 'president', 'founder'] and existing.get('title') not in ['ceo', 'president', 'founder']:
                unique_names[full_name] = name

    # Convert back to list and score
    final_names = list(unique_names.values())
    final_names = score_leadership_names(final_names)

    logger.info(f"Extracted {len(final_names)} leadership names")

    return final_names


def get_top_decision_makers(html: str, limit: int = 5) -> List[Dict]:
    """
    Get top decision-makers from website content.

    Args:
        html: HTML content
        limit: Maximum number of decision-makers to return

    Returns:
        List of top decision-makers
    """
    all_names = extract_leadership_names(html)
    return all_names[:limit]

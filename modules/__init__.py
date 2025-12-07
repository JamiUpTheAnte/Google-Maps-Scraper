"""
Lead Enrichment Modules
Comprehensive email quality filtering, leadership detection, and email verification
"""

from .email_filters import (
    filter_emails,
    extract_emails,
    is_company_domain,
    classify_email,
    score_email_quality,
    get_best_emails
)

from .website_crawler import (
    PriorityWebsiteCrawler,
    get_priority_urls,
    is_priority_url,
    extract_links_from_html
)

from .name_extractor import (
    extract_leadership_names,
    get_top_decision_makers,
    extract_names_with_titles
)

from .email_verifier import (
    EmailPatternGenerator,
    MailboxLayerVerifier,
    EmailEnricher,
    generate_email_patterns,
    verify_email_mailboxlayer
)

from .lead_enricher import (
    LeadEnrichmentPipeline,
    create_enrichment_pipeline
)

__all__ = [
    # Email filters
    'filter_emails',
    'extract_emails',
    'is_company_domain',
    'classify_email',
    'score_email_quality',
    'get_best_emails',

    # Website crawler
    'PriorityWebsiteCrawler',
    'get_priority_urls',
    'is_priority_url',
    'extract_links_from_html',

    # Name extractor
    'extract_leadership_names',
    'get_top_decision_makers',
    'extract_names_with_titles',

    # Email verifier
    'EmailPatternGenerator',
    'MailboxLayerVerifier',
    'EmailEnricher',
    'generate_email_patterns',
    'verify_email_mailboxlayer',

    # Lead enricher
    'LeadEnrichmentPipeline',
    'create_enrichment_pipeline'
]

__version__ = '1.0.0'

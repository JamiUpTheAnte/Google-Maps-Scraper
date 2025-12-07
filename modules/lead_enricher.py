"""
Lead Enrichment Pipeline
Orchestrates all enrichment modules to produce high-quality leads
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from .email_filters import (
    filter_emails, extract_emails, is_company_domain,
    score_email_quality
)
from .website_crawler import PriorityWebsiteCrawler
from .name_extractor import extract_leadership_names, get_top_decision_makers
from .email_verifier import EmailEnricher, MailboxLayerVerifier

logger = logging.getLogger(__name__)


class LeadEnrichmentPipeline:
    """
    Complete pipeline for enriching leads with high-quality contact information.
    """

    def __init__(self,
                 rate_limiter=None,
                 mailbox_api_key: Optional[str] = None,
                 enable_email_verification: bool = True,
                 max_pages_per_site: int = 10,
                 max_decision_makers: int = 5):
        """
        Initialize enrichment pipeline.

        Args:
            rate_limiter: RateLimitedScraper instance for fetching URLs
            mailbox_api_key: MailboxLayer API key for email verification
            enable_email_verification: Whether to verify emails with MailboxLayer
            max_pages_per_site: Maximum pages to crawl per website
            max_decision_makers: Maximum decision-makers to extract per company
        """
        self.rate_limiter = rate_limiter
        self.enable_verification = enable_email_verification and mailbox_api_key is not None

        # Initialize modules
        self.crawler = PriorityWebsiteCrawler(
            rate_limiter=rate_limiter,
            max_pages=max_pages_per_site
        )

        # Initialize email verifier if API key provided
        if mailbox_api_key and enable_email_verification:
            self.mailbox_verifier = MailboxLayerVerifier(
                api_key=mailbox_api_key,
                rate_limit_delay=1.0
            )
            self.email_enricher = EmailEnricher(mailbox_verifier=self.mailbox_verifier)
        else:
            self.mailbox_verifier = None
            self.email_enricher = EmailEnricher(mailbox_verifier=None)

        self.max_decision_makers = max_decision_makers

        logger.info(f"Lead Enrichment Pipeline initialized (verification: {self.enable_verification})")

    def enrich_lead(self, website_url: str, company_name: str = None,
                   phone: str = None, location: str = None) -> Dict:
        """
        Enrich a single lead with comprehensive contact information.

        Pipeline steps:
        1. Crawl website (homepage + priority pages)
        2. Extract all emails from crawled pages
        3. Filter emails by quality
        4. Extract leadership names
        5. Generate email patterns for decision-makers
        6. Verify generated emails (if enabled)
        7. Return enriched lead

        Args:
            website_url: Company website URL
            company_name: Company name (optional)
            phone: Phone number (optional)
            location: Location/city (optional)

        Returns:
            Enriched lead dictionary
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Enriching lead: {website_url}")
        logger.info(f"{'='*60}")

        result = {
            'website': website_url,
            'company': company_name or '',
            'phone': phone or '',
            'location': location or '',
            'enriched_at': datetime.now().isoformat(),
            'status': 'failed',

            # Raw data
            'pages_crawled': [],
            'priority_pages': [],
            'raw_emails': [],

            # Filtered data
            'emails': [],
            'filtered_emails': [],
            'best_emails': [],

            # Leadership
            'leadership': [],
            'decision_makers': [],

            # Quality metrics
            'quality_score': 0,
            'has_verified_emails': False,
            'has_decision_maker_emails': False
        }

        try:
            # Step 1: Crawl website
            logger.info("Step 1: Crawling website...")
            crawl_result = self.crawler.crawl_website(website_url)

            result['pages_crawled'] = crawl_result['crawled_pages']
            result['priority_pages'] = crawl_result['priority_pages']

            if not crawl_result['all_html']:
                logger.warning("No HTML content retrieved")
                return result

            logger.info(f"✓ Crawled {len(crawl_result['crawled_pages'])} pages")

            # Step 2: Extract emails from all crawled content
            logger.info("Step 2: Extracting emails...")
            raw_emails = extract_emails(crawl_result['all_html'])
            result['raw_emails'] = raw_emails
            logger.info(f"✓ Found {len(raw_emails)} raw emails")

            # Step 3: Filter emails by quality
            logger.info("Step 3: Filtering emails...")
            filtered = filter_emails(
                raw_emails,
                website_url=website_url,
                min_score=50,
                exclude_generic=False
            )

            result['filtered_emails'] = filtered
            result['emails'] = [item['email'] for item in filtered]

            # Get best emails (person-specific, high score)
            best_emails = [
                item['email'] for item in filtered
                if item['classification'] == 'person_or_good' and item['score'] >= 70
            ]
            result['best_emails'] = best_emails

            logger.info(f"✓ Filtered to {len(filtered)} quality emails ({len(best_emails)} high-quality)")

            # Step 4: Extract leadership names
            logger.info("Step 4: Extracting leadership names...")
            leadership = extract_leadership_names(crawl_result['all_html'])
            result['leadership'] = leadership

            top_decision_makers = leadership[:self.max_decision_makers]
            logger.info(f"✓ Found {len(leadership)} leadership names ({len(top_decision_makers)} top)")

            # Step 5 & 6: Generate and verify decision-maker emails
            if top_decision_makers:
                logger.info("Step 5-6: Generating and verifying decision-maker emails...")

                enriched_leaders = self.email_enricher.enrich_leadership_with_emails(
                    leadership_names=top_decision_makers,
                    website_url=website_url,
                    verify=self.enable_verification,
                    max_per_person=3
                )

                result['decision_makers'] = enriched_leaders

                # Count verified emails
                verified_count = sum(1 for dm in enriched_leaders if dm.get('email_verified', False))
                logger.info(f"✓ Generated emails for {len(enriched_leaders)} decision-makers ({verified_count} verified)")

                result['has_decision_maker_emails'] = len(enriched_leaders) > 0
                result['has_verified_emails'] = verified_count > 0

            # Step 7: Calculate quality score
            quality_score = self._calculate_quality_score(result)
            result['quality_score'] = quality_score
            result['status'] = 'success'

            logger.info(f"\n{'='*60}")
            logger.info(f"✓ Enrichment complete! Quality Score: {quality_score}/100")
            logger.info(f"  - Pages crawled: {len(result['pages_crawled'])}")
            logger.info(f"  - Quality emails: {len(result['best_emails'])}")
            logger.info(f"  - Decision-makers: {len(result['decision_makers'])}")
            logger.info(f"  - Verified emails: {sum(1 for dm in result['decision_makers'] if dm.get('email_verified', False))}")
            logger.info(f"{'='*60}\n")

        except Exception as e:
            logger.error(f"Error enriching lead {website_url}: {e}", exc_info=True)
            result['error'] = str(e)

        return result

    def _calculate_quality_score(self, result: Dict) -> int:
        """
        Calculate overall lead quality score (0-100).

        Args:
            result: Enriched lead result

        Returns:
            Quality score (0-100)
        """
        score = 0

        # Has website content (20 points)
        if len(result['pages_crawled']) > 0:
            score += 20

        # Has quality emails (25 points)
        if len(result['best_emails']) > 0:
            score += 15
            if len(result['best_emails']) >= 2:
                score += 10

        # Has decision-makers (30 points)
        if len(result['decision_makers']) > 0:
            score += 15
            if len(result['decision_makers']) >= 2:
                score += 10
            if result['has_verified_emails']:
                score += 5

        # Has verified emails (25 points)
        if result['has_verified_emails']:
            score += 20
            verified_count = sum(1 for dm in result['decision_makers'] if dm.get('email_verified', False))
            if verified_count >= 2:
                score += 5

        return min(100, score)

    def enrich_leads_batch(self, leads: List[Dict]) -> List[Dict]:
        """
        Enrich multiple leads.

        Args:
            leads: List of lead dictionaries with 'website' key

        Returns:
            List of enriched leads
        """
        enriched = []

        for i, lead in enumerate(leads, 1):
            logger.info(f"\n[{i}/{len(leads)}] Processing lead...")

            website = lead.get('website', '')
            company = lead.get('company', '')
            phone = lead.get('phone', '')
            location = lead.get('location', '')

            if not website:
                logger.warning(f"Skipping lead {i}: no website")
                continue

            enriched_lead = self.enrich_lead(
                website_url=website,
                company_name=company,
                phone=phone,
                location=location
            )

            enriched.append(enriched_lead)

        return enriched

    def get_summary_stats(self, enriched_leads: List[Dict]) -> Dict:
        """
        Get summary statistics for enriched leads.

        Args:
            enriched_leads: List of enriched lead dictionaries

        Returns:
            Summary statistics
        """
        total = len(enriched_leads)
        successful = sum(1 for lead in enriched_leads if lead['status'] == 'success')

        with_emails = sum(1 for lead in enriched_leads if len(lead['best_emails']) > 0)
        with_decision_makers = sum(1 for lead in enriched_leads if len(lead['decision_makers']) > 0)
        with_verified = sum(1 for lead in enriched_leads if lead['has_verified_emails'])

        avg_quality = sum(lead['quality_score'] for lead in enriched_leads) / total if total > 0 else 0

        high_quality = sum(1 for lead in enriched_leads if lead['quality_score'] >= 70)

        return {
            'total_leads': total,
            'successful': successful,
            'with_quality_emails': with_emails,
            'with_decision_makers': with_decision_makers,
            'with_verified_emails': with_verified,
            'average_quality_score': round(avg_quality, 1),
            'high_quality_leads': high_quality,
            'success_rate': round(successful / total * 100, 1) if total > 0 else 0
        }


def create_enrichment_pipeline(rate_limiter=None, mailbox_api_key: Optional[str] = None,
                               enable_verification: bool = True) -> LeadEnrichmentPipeline:
    """
    Factory function to create enrichment pipeline.

    Args:
        rate_limiter: RateLimitedScraper instance
        mailbox_api_key: MailboxLayer API key
        enable_verification: Enable email verification

    Returns:
        LeadEnrichmentPipeline instance
    """
    return LeadEnrichmentPipeline(
        rate_limiter=rate_limiter,
        mailbox_api_key=mailbox_api_key,
        enable_email_verification=enable_verification
    )

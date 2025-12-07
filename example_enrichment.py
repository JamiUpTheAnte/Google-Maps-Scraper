"""
Example: Using the Lead Enrichment Pipeline
Demonstrates how to enrich leads with email verification and decision-maker extraction
"""

import os
from scraper import RateLimitedScraper
from modules.lead_enricher import LeadEnrichmentPipeline
from config import Config
import json


def example_basic_enrichment():
    """Example 1: Basic enrichment without email verification"""
    print("\n" + "="*60)
    print("Example 1: Basic Enrichment (No Email Verification)")
    print("="*60)

    scraper = RateLimitedScraper(
        min_delay=2.0,
        max_delay=4.0,
        enable_enrichment=True,
        mailbox_api_key=None  # No verification
    )

    # Enrich a single lead
    lead = scraper.scrape_website(
        url='https://www.example-construction.com',
        company='Example Construction Co',
        location='Atlanta'
    )

    print(f"\nResults:")
    print(f"  Company: {lead['company']}")
    print(f"  Quality Score: {lead['quality_score']}/100")
    print(f"  Pages Crawled: {len(lead['pages_crawled'])}")
    print(f"  Quality Emails: {len(lead['best_emails'])}")
    print(f"  Decision Makers: {len(lead['decision_makers'])}")

    if lead['decision_makers']:
        print(f"\n  Top Decision Maker:")
        dm = lead['decision_makers'][0]
        print(f"    Name: {dm['full_name']}")
        print(f"    Title: {dm['title']}")
        print(f"    Email: {dm.get('email', 'N/A')}")


def example_with_verification():
    """Example 2: Full enrichment with email verification"""
    print("\n" + "="*60)
    print("Example 2: Full Enrichment with Email Verification")
    print("="*60)

    # Load API key from environment
    api_key = os.getenv('MAILBOXLAYER_API_KEY')

    if not api_key:
        print("\n⚠️  MAILBOXLAYER_API_KEY not found in environment.")
        print("Set it in .env file to enable email verification.")
        return

    scraper = RateLimitedScraper(
        min_delay=2.0,
        max_delay=4.0,
        enable_enrichment=True,
        mailbox_api_key=api_key
    )

    # Enrich with verification
    lead = scraper.scrape_website(
        url='https://www.example-company.com',
        company='Example Company',
        location='New York'
    )

    print(f"\nResults:")
    print(f"  Company: {lead['company']}")
    print(f"  Quality Score: {lead['quality_score']}/100")
    print(f"  Has Verified Emails: {lead['has_verified_emails']}")

    if lead['decision_makers']:
        print(f"\n  Decision Makers with Verified Emails:")
        for dm in lead['decision_makers']:
            verified = "✓" if dm.get('email_verified') else "✗"
            print(f"    {verified} {dm['full_name']} ({dm['title']}) - {dm.get('email', 'N/A')}")


def example_batch_enrichment():
    """Example 3: Batch enrichment of multiple leads"""
    print("\n" + "="*60)
    print("Example 3: Batch Enrichment")
    print("="*60)

    # Create enrichment pipeline
    pipeline = LeadEnrichmentPipeline(
        mailbox_api_key=os.getenv('MAILBOXLAYER_API_KEY'),
        enable_email_verification=bool(os.getenv('MAILBOXLAYER_API_KEY')),
        max_pages_per_site=5,
        max_decision_makers=3
    )

    # Batch of leads to enrich
    leads_to_enrich = [
        {
            'website': 'https://company1.com',
            'company': 'Company 1',
            'location': 'Atlanta'
        },
        {
            'website': 'https://company2.com',
            'company': 'Company 2',
            'location': 'Boston'
        },
        {
            'website': 'https://company3.com',
            'company': 'Company 3',
            'location': 'Seattle'
        }
    ]

    print(f"\nEnriching {len(leads_to_enrich)} leads...")

    enriched = pipeline.enrich_leads_batch(leads_to_enrich)

    # Get statistics
    stats = pipeline.get_summary_stats(enriched)

    print(f"\n📊 Summary Statistics:")
    print(f"  Total Leads: {stats['total_leads']}")
    print(f"  Successful: {stats['successful']}")
    print(f"  With Quality Emails: {stats['with_quality_emails']}")
    print(f"  With Decision Makers: {stats['with_decision_makers']}")
    print(f"  With Verified Emails: {stats['with_verified_emails']}")
    print(f"  Average Quality Score: {stats['average_quality_score']}/100")
    print(f"  High Quality Leads: {stats['high_quality_leads']}")


def example_export_for_crm():
    """Example 4: Export enriched data for CRM/Airtable"""
    print("\n" + "="*60)
    print("Example 4: Export for CRM Integration")
    print("="*60)

    scraper = RateLimitedScraper(
        min_delay=2.0,
        max_delay=4.0,
        enable_enrichment=True,
        mailbox_api_key=os.getenv('MAILBOXLAYER_API_KEY')
    )

    # Enrich leads
    leads = []
    websites = [
        'https://company1.com',
        'https://company2.com',
        'https://company3.com'
    ]

    for url in websites:
        lead = scraper.scrape_website(url)
        leads.append(lead)

    # Transform for CRM
    crm_records = []

    for lead in leads:
        # Only export high-quality leads
        if lead['quality_score'] < 60:
            continue

        # Get top decision-maker
        decision_maker = lead['decision_makers'][0] if lead['decision_makers'] else None

        crm_record = {
            'Company': lead['company'],
            'Website': lead['website'],
            'Quality Score': lead['quality_score'],
            'Decision Maker Name': decision_maker['full_name'] if decision_maker else '',
            'Email': decision_maker.get('email', '') if decision_maker else '',
            'Email Verified': decision_maker.get('email_verified', False) if decision_maker else False,
            'Title': decision_maker.get('title', '') if decision_maker else '',
            'Phone': lead.get('phone', ''),
            'Location': lead.get('location', ''),
            'All Emails': ', '.join(lead['best_emails']),
            'Enriched At': lead['enriched_at']
        }

        crm_records.append(crm_record)

    # Save as JSON
    output_file = 'crm_export.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(crm_records, f, indent=2)

    print(f"\n✓ Exported {len(crm_records)} high-quality leads to {output_file}")
    print(f"\nSample record:")
    if crm_records:
        print(json.dumps(crm_records[0], indent=2))


def example_custom_filtering():
    """Example 5: Custom email filtering"""
    print("\n" + "="*60)
    print("Example 5: Custom Email Filtering")
    print("="*60)

    from modules.email_filters import filter_emails, score_email_quality

    # Sample emails from a website
    raw_emails = [
        'john.doe@company.com',
        'jane.smith@company.com',
        'info@company.com',
        'noreply@company.com',
        'sales@company.com',
        'ceo@company.com',
        'random@gmail.com'
    ]

    print(f"\nRaw emails: {len(raw_emails)}")

    # Filter and score
    filtered = filter_emails(
        raw_emails,
        website_url='https://company.com',
        min_score=60,
        exclude_generic=False
    )

    print(f"\nFiltered emails: {len(filtered)}")
    print("\nEmail Quality Scores:")

    for item in filtered:
        print(f"  {item['email']:30} Score: {item['score']:3}  Type: {item['classification']:15}  Accept: {item['accept']}")


def example_name_extraction():
    """Example 6: Leadership name extraction"""
    print("\n" + "="*60)
    print("Example 6: Leadership Name Extraction")
    print("="*60)

    from modules.name_extractor import extract_leadership_names

    # Sample HTML content (simulated)
    sample_html = """
    <html>
        <head><title>Company Leadership</title></head>
        <body>
            <div class="team">
                <h2>Our Leadership Team</h2>
                <div class="person">
                    <h3>John Smith</h3>
                    <p>Chief Executive Officer</p>
                </div>
                <div class="person">
                    <h3>Jane Doe</h3>
                    <p>Chief Technology Officer</p>
                </div>
                <div class="person">
                    <h3>Bob Johnson</h3>
                    <p>Vice President of Sales</p>
                </div>
            </div>
        </body>
    </html>
    """

    leaders = extract_leadership_names(sample_html)

    print(f"\nFound {len(leaders)} leadership names:")
    for leader in leaders:
        print(f"  {leader['full_name']:20} - {leader['title']:30} (score: {leader['score']})")


def example_email_pattern_generation():
    """Example 7: Email pattern generation"""
    print("\n" + "="*60)
    print("Example 7: Email Pattern Generation")
    print("="*60)

    from modules.email_verifier import generate_email_patterns

    # Generate patterns for a name
    first = "John"
    last = "Smith"
    domain = "company.com"

    patterns = generate_email_patterns(first, last, domain)

    print(f"\nGenerated {len(patterns)} email patterns for {first} {last}:")
    for i, pattern in enumerate(patterns, 1):
        print(f"  {i}. {pattern}")


if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Lead Enrichment Pipeline - Examples")
    print("="*60)

    # Run examples
    try:
        example_basic_enrichment()
    except Exception as e:
        print(f"\n⚠️  Example 1 failed: {e}")

    try:
        example_custom_filtering()
    except Exception as e:
        print(f"\n⚠️  Example 5 failed: {e}")

    try:
        example_name_extraction()
    except Exception as e:
        print(f"\n⚠️  Example 6 failed: {e}")

    try:
        example_email_pattern_generation()
    except Exception as e:
        print(f"\n⚠️  Example 7 failed: {e}")

    # Examples requiring API key
    if os.getenv('MAILBOXLAYER_API_KEY'):
        try:
            example_with_verification()
        except Exception as e:
            print(f"\n⚠️  Example 2 failed: {e}")

        try:
            example_batch_enrichment()
        except Exception as e:
            print(f"\n⚠️  Example 3 failed: {e}")

        try:
            example_export_for_crm()
        except Exception as e:
            print(f"\n⚠️  Example 4 failed: {e}")
    else:
        print("\n⚠️  Skipping verification examples (MAILBOXLAYER_API_KEY not set)")

    print("\n" + "="*60)
    print("✓ Examples complete!")
    print("="*60 + "\n")

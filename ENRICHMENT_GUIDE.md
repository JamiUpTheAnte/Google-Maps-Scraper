# Lead Enrichment Guide

## Overview

This upgraded Google Maps Scraper now includes sophisticated lead enrichment capabilities:

✅ **Email Quality Filtering** - Filters out junk emails, prioritizes company domains
✅ **Priority Website Crawling** - Targets contact/about/team pages
✅ **Leadership Name Extraction** - Detects decision-makers from website content
✅ **Email Pattern Generation** - Creates probable email addresses from names
✅ **Email Verification** - Validates emails via MailboxLayer API
✅ **Quality Scoring** - Scores each lead 0-100 based on data quality

---

## Architecture

```
Google-Maps-Scraper/
├── modules/
│   ├── __init__.py              # Package initialization
│   ├── email_filters.py         # Email quality filtering
│   ├── website_crawler.py       # Priority page crawler
│   ├── name_extractor.py        # Leadership name detection
│   ├── email_verifier.py        # Pattern generation + verification
│   └── lead_enricher.py         # Main enrichment pipeline
├── app.py                       # Flask API (enrichment-enabled)
├── scraper.py                   # Scraper (enrichment-enabled)
├── config.py                    # Configuration management
└── .env.example                 # Environment variables template
```

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
cp .env.example .env
# Edit .env and add your MailboxLayer API key
```

```ini
MAILBOXLAYER_API_KEY=your_api_key_here
ENABLE_ENRICHMENT=true
```

### 3. Run with Enrichment

#### Option A: Flask API

```bash
python app.py
```

Make API request:

```bash
curl -X POST http://localhost:5000/api/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "business_type": "construction company",
    "location": "Atlanta",
    "num_results": 10,
    "enable_enrichment": true,
    "mailbox_api_key": "your_key_here"
  }'
```

#### Option B: Python Script

```python
from scraper import RateLimitedScraper

scraper = RateLimitedScraper(
    min_delay=3.0,
    max_delay=7.0,
    enable_enrichment=True,
    mailbox_api_key='your_mailboxlayer_api_key'
)

lead = scraper.scrape_website(
    url='https://example-construction.com',
    company='Example Construction',
    location='Atlanta'
)

print(f"Quality Score: {lead['quality_score']}/100")
print(f"Decision Makers: {len(lead['decision_makers'])}")
print(f"Verified Emails: {lead['has_verified_emails']}")
```

---

## Data Flow Pipeline

```
1. Google Search
   └─> Collect company websites

2. Priority Crawling
   ├─> Homepage
   ├─> /contact
   ├─> /about
   ├─> /team
   └─> /leadership

3. Email Extraction
   ├─> Extract raw emails
   ├─> Filter by domain (company-only)
   ├─> Classify email types
   └─> Score quality (0-100)

4. Leadership Detection
   ├─> Find names + titles
   ├─> Extract decision-makers
   └─> Rank by importance

5. Email Generation
   ├─> Generate patterns (firstname.lastname@domain)
   ├─> Verify with MailboxLayer
   └─> Return best match

6. Output
   └─> Enriched lead with quality score
```

---

## Module Details

### 1. Email Filters (`email_filters.py`)

**Functions:**

```python
from modules.email_filters import filter_emails, classify_email, score_email_quality

# Filter emails by quality
filtered = filter_emails(
    emails=['john.doe@company.com', 'info@company.com'],
    website_url='https://company.com',
    min_score=50,
    exclude_generic=False
)

# Classify email type
classification = classify_email('noreply@company.com')
# Returns: 'dev_junk', 'role_generic', or 'person_or_good'

# Score email quality
score = score_email_quality('john@company.com', 'https://company.com')
# Returns: {'score': 85, 'accept': True, 'reasons': [...]}
```

**Email Classifications:**

- `dev_junk`: noreply@, admin@, webmaster@ (filtered out)
- `role_generic`: info@, contact@, sales@ (low priority)
- `person_or_good`: john.doe@, jane.smith@ (high priority)

**Blacklisted Domains:**

- Free providers: gmail.com, yahoo.com, hotmail.com
- Temp emails: mailinator.com, guerrillamail.com

---

### 2. Website Crawler (`website_crawler.py`)

**Priority Pages:**

Automatically finds and crawls:
- `/contact`, `/contact-us`
- `/about`, `/about-us`
- `/team`, `/our-team`
- `/leadership`, `/management`
- `/founders`, `/executives`

**Usage:**

```python
from modules.website_crawler import PriorityWebsiteCrawler

crawler = PriorityWebsiteCrawler(
    rate_limiter=scraper,
    max_pages=10
)

result = crawler.crawl_website('https://company.com')

print(result['crawled_pages'])      # Pages crawled
print(result['priority_pages'])     # High-value pages found
print(result['all_html'])           # Combined HTML content
```

---

### 3. Name Extractor (`name_extractor.py`)

**Detected Titles:**

- C-level: CEO, CTO, CFO, COO, CMO
- Executives: President, VP, Director
- Founders: Founder, Co-Founder, Owner
- Management: Manager, Head of, Partner

**Usage:**

```python
from modules.name_extractor import extract_leadership_names, get_top_decision_makers

# Extract all leadership
leaders = extract_leadership_names(html_content)

# Get top 5 decision-makers
top_leaders = get_top_decision_makers(html_content, limit=5)

for leader in top_leaders:
    print(f"{leader['full_name']} - {leader['title']}")
```

**Output Example:**

```json
[
  {
    "first_name": "John",
    "last_name": "Smith",
    "full_name": "John Smith",
    "title": "ceo",
    "confidence": "high",
    "score": 100
  }
]
```

---

### 4. Email Verifier (`email_verifier.py`)

**Pattern Generation:**

```python
from modules.email_verifier import generate_email_patterns

patterns = generate_email_patterns('John', 'Doe', 'company.com')
# Returns:
# [
#   'john.doe@company.com',
#   'johndoe@company.com',
#   'jdoe@company.com',
#   'john_doe@company.com',
#   ...
# ]
```

**MailboxLayer Verification:**

```python
from modules.email_verifier import MailboxLayerVerifier

verifier = MailboxLayerVerifier(api_key='your_key')

is_valid, metadata = verifier.verify_email('john.doe@company.com')

if is_valid:
    print(f"✓ Email is valid (score: {metadata['score']})")
else:
    print(f"✗ Email is invalid")
```

**Verification Criteria:**

- ✅ Format valid
- ✅ MX records exist
- ✅ Not disposable email
- ✅ Quality score ≥ 0.45

---

### 5. Lead Enricher (`lead_enricher.py`)

**Main Pipeline:**

```python
from modules.lead_enricher import LeadEnrichmentPipeline

pipeline = LeadEnrichmentPipeline(
    rate_limiter=scraper,
    mailbox_api_key='your_key',
    enable_email_verification=True,
    max_pages_per_site=10,
    max_decision_makers=5
)

# Enrich single lead
lead = pipeline.enrich_lead(
    website_url='https://company.com',
    company_name='Company Inc',
    phone='555-1234',
    location='Atlanta'
)

# Batch enrichment
leads = pipeline.enrich_leads_batch([
    {'website': 'https://company1.com', 'company': 'Company 1'},
    {'website': 'https://company2.com', 'company': 'Company 2'}
])

# Get statistics
stats = pipeline.get_summary_stats(leads)
print(f"Average quality: {stats['average_quality_score']}/100")
```

**Enriched Lead Output:**

```json
{
  "website": "https://company.com",
  "company": "Company Inc",
  "phone": "555-1234",
  "location": "Atlanta",
  "quality_score": 85,

  "emails": ["john.doe@company.com", "contact@company.com"],
  "best_emails": ["john.doe@company.com"],

  "decision_makers": [
    {
      "first_name": "John",
      "last_name": "Doe",
      "full_name": "John Doe",
      "title": "ceo",
      "email": "john.doe@company.com",
      "email_verified": true,
      "email_patterns": ["john.doe@company.com", "jdoe@company.com"],
      "score": 100
    }
  ],

  "has_verified_emails": true,
  "has_decision_maker_emails": true,
  "status": "success"
}
```

---

## Quality Scoring System

Each lead receives a quality score (0-100):

| Score Range | Quality | Criteria |
|-------------|---------|----------|
| 90-100 | Excellent | Verified decision-maker emails + company emails |
| 70-89 | Good | Decision-makers found + quality emails |
| 50-69 | Fair | Some emails or decision-makers |
| 0-49 | Poor | Minimal contact info |

**Scoring Formula:**

- Pages crawled: +20 points
- Quality emails found: +15-25 points
- Decision-makers found: +15-30 points
- Verified emails: +20-25 points

---

## Integration Examples

### n8n Workflow Integration

```json
{
  "nodes": [
    {
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "http://your-server:5000/api/scrape",
        "method": "POST",
        "bodyParameters": {
          "business_type": "construction company",
          "location": "Atlanta",
          "num_results": 50,
          "enable_enrichment": true,
          "mailbox_api_key": "={{$env.MAILBOXLAYER_API_KEY}}"
        }
      }
    },
    {
      "type": "n8n-nodes-base.airtable",
      "parameters": {
        "operation": "create",
        "table": "Leads",
        "fields": {
          "Company": "={{$json.company}}",
          "Website": "={{$json.website}}",
          "Decision Maker": "={{$json.decision_makers[0].full_name}}",
          "Email": "={{$json.decision_makers[0].email}}",
          "Title": "={{$json.decision_makers[0].title}}",
          "Quality Score": "={{$json.quality_score}}",
          "Verified": "={{$json.has_verified_emails}}"
        }
      }
    }
  ]
}
```

### Airtable Schema

Recommended Airtable fields:

- **Company** (Single line text)
- **Website** (URL)
- **Quality Score** (Number, 0-100)
- **Decision Maker Name** (Single line text)
- **Email** (Email)
- **Email Verified** (Checkbox)
- **Title** (Single select: CEO, CTO, CFO, etc.)
- **Phone** (Phone number)
- **Location** (Single line text)
- **All Emails** (Long text)
- **Enriched At** (Date)

### Python Script for Outbound Omega

```python
from scraper import RateLimitedScraper
import json

# Initialize scraper with enrichment
scraper = RateLimitedScraper(
    enable_enrichment=True,
    mailbox_api_key='your_mailboxlayer_key'
)

# Scrape leads
leads = []
for url in company_websites:
    lead = scraper.scrape_website(url)

    # Only keep high-quality leads
    if lead['quality_score'] >= 70:
        leads.append(lead)

# Export for outbound campaign
outbound_data = []
for lead in leads:
    if lead['decision_makers']:
        dm = lead['decision_makers'][0]  # Top decision-maker

        outbound_data.append({
            'first_name': dm['first_name'],
            'last_name': dm['last_name'],
            'email': dm['email'],
            'company': lead['company'],
            'title': dm['title'],
            'website': lead['website'],
            'personalization_data': {
                'company_name': lead['company'],
                'title': dm['title']
            }
        })

# Save for Outbound Omega
with open('outbound_leads.json', 'w') as f:
    json.dump(outbound_data, f, indent=2)
```

### AI Cold Outreach Prompt Generator

```python
# Generate personalized cold email prompts
for lead in outbound_data:
    prompt = f"""
Generate a personalized cold email for:
- Name: {lead['first_name']} {lead['last_name']}
- Title: {lead['title']}
- Company: {lead['company']}
- Industry: Construction

Email should:
1. Reference their role as {lead['title']}
2. Mention {lead['company']} specifically
3. Focus on [your value proposition]
4. Include a clear CTA
5. Be under 100 words

Tone: Professional, helpful, not salesy
"""

    # Send to your AI prompt generator
    personalized_email = generate_with_ai(prompt)
    lead['email_body'] = personalized_email
```

---

## API Reference

### POST /api/scrape

Start a scraping job with enrichment.

**Request:**

```json
{
  "business_type": "construction company",
  "location": "Atlanta",
  "num_results": 50,
  "min_delay": 3.0,
  "max_delay": 7.0,
  "enable_enrichment": true,
  "mailbox_api_key": "your_mailboxlayer_api_key"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Scraping job started",
  "query": "construction company Atlanta",
  "enrichment_enabled": true
}
```

### GET /api/status

Get current scraping job status.

**Response:**

```json
{
  "is_running": true,
  "progress": 15,
  "total": 50,
  "status": "running",
  "message": "Scraping 15/50: https://example.com..."
}
```

### GET /api/results

Get enriched results.

**Response:**

```json
{
  "success": true,
  "count": 50,
  "results": [
    {
      "website": "https://company.com",
      "quality_score": 85,
      "decision_makers": [...],
      ...
    }
  ]
}
```

---

## Performance & Best Practices

### Rate Limiting

- **Default delays:** 3-7 seconds between requests
- **Extended breaks:** Every 10 requests (5-10 second pause)
- **Recommended:** Use min_delay=3.0, max_delay=7.0 for stability

### MailboxLayer API Limits

- **Free tier:** 250 requests/month
- **Paid tiers:** Up to 100,000/month
- **Rate limit:** 1 request/second (automatically enforced)

### Cost Optimization

```python
# Only verify top decision-maker (saves API calls)
pipeline = LeadEnrichmentPipeline(
    mailbox_api_key='your_key',
    max_decision_makers=1  # Only verify CEO/top person
)

# Batch processing with checkpoints
for i, url in enumerate(urls):
    lead = scraper.scrape_website(url)
    leads.append(lead)

    # Save every 10 leads
    if i % 10 == 0:
        save_to_csv(leads, f'checkpoint_{i}.csv')
```

### Quality Thresholds

```python
# Filter leads by quality
high_quality = [l for l in leads if l['quality_score'] >= 70]
with_verified = [l for l in leads if l['has_verified_emails']]
with_decision_makers = [l for l in leads if l['decision_makers']]
```

---

## Troubleshooting

### "No decision-makers found"

- Check if website has `/about`, `/team`, or `/leadership` pages
- Some websites may not publish leadership information
- Try increasing `max_pages_per_site` to crawl more pages

### "Email verification failing"

- Verify MailboxLayer API key is correct
- Check API quota (free tier has 250/month limit)
- Some email servers block verification requests

### "Low quality scores"

- Website may have minimal contact information
- Try different company websites
- Use `min_score` parameter to filter low-quality leads

### "Rate limited by Google"

- Increase delays: `min_delay=5.0, max_delay=10.0`
- Reduce `num_results`
- Use residential proxies (not included, configure separately)

---

## Advanced Configuration

### Custom Email Patterns

```python
from modules.email_verifier import EmailPatternGenerator

# Extend pattern generator
class CustomPatternGenerator(EmailPatternGenerator):
    @staticmethod
    def generate_patterns(first, last, domain):
        patterns = EmailPatternGenerator.generate_patterns(first, last, domain)

        # Add custom patterns
        if first and last:
            patterns.append(f"{last}{first[0]}@{domain}")  # doej@company.com

        return patterns
```

### Custom Quality Scoring

```python
# Override quality calculation
def custom_quality_score(lead):
    score = 0

    # Your custom scoring logic
    if lead['decision_makers']:
        score += 50
    if lead['has_verified_emails']:
        score += 30
    if len(lead['best_emails']) > 2:
        score += 20

    return min(100, score)
```

---

## License & Support

MIT License - Use freely for commercial purposes.

For issues or questions:
- GitHub Issues: [Link to repository]
- Email: [Your support email]

---

## Credits

Built with:
- BeautifulSoup4 (HTML parsing)
- Requests (HTTP client)
- Flask (API framework)
- MailboxLayer (Email verification)
- googlesearch-python (Google search)

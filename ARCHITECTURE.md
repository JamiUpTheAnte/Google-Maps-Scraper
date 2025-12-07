# System Architecture

## Overview

The Google Maps Scraper has been upgraded with a modular lead enrichment pipeline that dramatically improves email quality and provides verified decision-maker contacts.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Google Maps Scraper                          │
│                 with Lead Enrichment Pipeline                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  INPUT: Google Search Query                                      │
│  "construction company Atlanta"                                  │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 1: Google Search                                           │
│  ├─ googlesearch-python API                                      │
│  ├─ Rate limiting (2-4s delays)                                  │
│  └─ Output: List of company websites                             │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 2: Priority Website Crawling                               │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  PriorityWebsiteCrawler (website_crawler.py)             │   │
│  │  ├─ Crawl homepage                                        │   │
│  │  ├─ Extract all links                                     │   │
│  │  ├─ Identify priority pages:                              │   │
│  │  │  • /contact, /about, /team, /leadership               │   │
│  │  ├─ Crawl priority pages (max 10)                         │   │
│  │  └─ Return combined HTML content                          │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 3: Email Extraction & Filtering                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  EmailFilters (email_filters.py)                          │   │
│  │  ├─ Extract raw emails (regex + mailto links)             │   │
│  │  ├─ Filter by domain (company-only)                       │   │
│  │  ├─ Classify email types:                                 │   │
│  │  │  • dev_junk: noreply@, admin@                         │   │
│  │  │  • role_generic: info@, contact@                      │   │
│  │  │  • person_or_good: john.doe@                          │   │
│  │  ├─ Score quality (0-100)                                 │   │
│  │  ├─ Filter blacklisted domains (gmail, etc)               │   │
│  │  └─ Return ranked quality emails                          │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 4: Leadership Name Extraction                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  NameExtractor (name_extractor.py)                        │   │
│  │  ├─ Parse HTML for leadership sections                    │   │
│  │  ├─ Extract names + titles:                               │   │
│  │  │  • CEO, CTO, CFO, President, VP                       │   │
│  │  │  • Founder, Director, Manager                         │   │
│  │  ├─ Score by leadership level:                            │   │
│  │  │  • CEO: 100, President: 90, VP: 60                    │   │
│  │  ├─ Pattern matching for "Name, Title" formats            │   │
│  │  └─ Return ranked decision-makers                         │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 5: Email Pattern Generation                                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  EmailPatternGenerator (email_verifier.py)                │   │
│  │  ├─ For each decision-maker:                              │   │
│  │  │  • john.doe@company.com                               │   │
│  │  │  • johndoe@company.com                                │   │
│  │  │  • jdoe@company.com                                   │   │
│  │  │  • john_doe@company.com                               │   │
│  │  │  • j.doe@company.com                                  │   │
│  │  └─ Return patterns (sorted by probability)               │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 6: Email Verification (Optional)                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  MailboxLayerVerifier (email_verifier.py)                 │   │
│  │  ├─ For each pattern (max 3):                             │   │
│  │  │  • Call MailboxLayer API                              │   │
│  │  │  • Check: format, MX records, disposable              │   │
│  │  │  • Quality score >= 0.45                              │   │
│  │  ├─ Rate limit: 1 request/second                          │   │
│  │  ├─ Stop on first valid email                             │   │
│  │  └─ Return verified email or best guess                   │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 7: Lead Quality Scoring                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  LeadEnrichmentPipeline (lead_enricher.py)                │   │
│  │  ├─ Score components:                                     │   │
│  │  │  • Pages crawled: +20                                 │   │
│  │  │  • Quality emails: +15-25                             │   │
│  │  │  • Decision-makers: +15-30                            │   │
│  │  │  • Verified emails: +20-25                            │   │
│  │  ├─ Total score: 0-100                                    │   │
│  │  └─ Quality tiers:                                        │   │
│  │     • 90-100: Excellent                                  │   │
│  │     • 70-89: Good                                        │   │
│  │     • 50-69: Fair                                        │   │
│  │     • 0-49: Poor                                         │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  OUTPUT: Enriched Lead                                           │
│  {                                                                │
│    "company": "Example Construction Co",                          │
│    "website": "https://example.com",                              │
│    "quality_score": 85,                                           │
│    "best_emails": ["john.doe@example.com"],                       │
│    "decision_makers": [                                           │
│      {                                                            │
│        "full_name": "John Doe",                                   │
│        "title": "ceo",                                            │
│        "email": "john.doe@example.com",                           │
│        "email_verified": true                                     │
│      }                                                            │
│    ],                                                             │
│    "has_verified_emails": true                                    │
│  }                                                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Module Breakdown

### Core Modules

| Module | File | Purpose | Key Functions |
|--------|------|---------|---------------|
| **Email Filters** | `email_filters.py` | Email quality filtering | `filter_emails()`, `classify_email()`, `score_email_quality()` |
| **Website Crawler** | `website_crawler.py` | Priority page crawling | `PriorityWebsiteCrawler`, `get_priority_urls()` |
| **Name Extractor** | `name_extractor.py` | Leadership detection | `extract_leadership_names()`, `get_top_decision_makers()` |
| **Email Verifier** | `email_verifier.py` | Pattern generation + verification | `EmailPatternGenerator`, `MailboxLayerVerifier` |
| **Lead Enricher** | `lead_enricher.py` | Orchestration pipeline | `LeadEnrichmentPipeline` |

### Integration Layer

| Component | File | Purpose |
|-----------|------|---------|
| **Scraper** | `scraper.py` | Main scraping engine with enrichment support |
| **Flask API** | `app.py` | REST API for n8n/automation integration |
| **Config** | `config.py` | Centralized configuration management |

---

## Data Flow

```
Google Search
    │
    ├─> List of URLs
    │
    ▼
For each URL:
    │
    ├─> Crawl website (homepage + priority pages)
    │     └─> Extract HTML
    │
    ├─> Extract emails
    │     ├─> Raw extraction (regex + mailto)
    │     └─> Filter & score quality
    │
    ├─> Extract leadership names
    │     ├─> Parse HTML for titles
    │     └─> Rank by importance
    │
    ├─> Generate email patterns
    │     └─> firstname.lastname@domain.com, etc.
    │
    ├─> Verify emails (optional)
    │     └─> MailboxLayer API
    │
    └─> Calculate quality score
          └─> Output enriched lead
```

---

## Quality Assurance

### Email Quality Checks

1. **Format Validation**: Regex pattern matching
2. **Domain Filtering**: Company-domain only
3. **Blacklist Check**: Exclude free providers (gmail, yahoo)
4. **Classification**: dev_junk / role_generic / person_or_good
5. **Quality Scoring**: 0-100 based on multiple factors
6. **Verification** (optional): MailboxLayer API validation

### Lead Quality Metrics

- **Pages Crawled**: More pages = better data
- **Email Quality**: Person-specific > role-based > generic
- **Decision-Makers**: CEO > President > VP > Manager
- **Verification Status**: Verified > Unverified

---

## API Integration Points

### Input

```json
{
  "business_type": "construction company",
  "location": "Atlanta",
  "num_results": 50,
  "enable_enrichment": true,
  "mailbox_api_key": "your_api_key"
}
```

### Output

```json
{
  "website": "https://company.com",
  "company": "Company Inc",
  "quality_score": 85,
  "best_emails": ["john.doe@company.com"],
  "decision_makers": [
    {
      "full_name": "John Doe",
      "title": "ceo",
      "email": "john.doe@company.com",
      "email_verified": true,
      "score": 100
    }
  ],
  "has_verified_emails": true,
  "status": "success"
}
```

---

## Deployment Architecture

### Local Development

```
┌─────────────────┐
│   Developer     │
│   Machine       │
│                 │
│  ┌───────────┐  │
│  │ Flask App │  │
│  │ :5000     │  │
│  └───────────┘  │
└─────────────────┘
```

### Production (n8n Integration)

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│              │       │              │       │              │
│    n8n       │──────>│   Scraper    │──────>│  Airtable    │
│  Workflow    │ HTTP  │   API        │ Data  │   CRM        │
│              │       │  (Flask)     │       │              │
└──────────────┘       └──────────────┘       └──────────────┘
                              │
                              │ API Call
                              ▼
                       ┌──────────────┐
                       │ MailboxLayer │
                       │     API      │
                       └──────────────┘
```

### Recommended Stack

- **Server**: Ubuntu/Debian VPS
- **Python**: 3.8+
- **Web Server**: Gunicorn + Nginx (production)
- **Process Manager**: Supervisor or systemd
- **Monitoring**: Sentry (errors) + Prometheus (metrics)

---

## Performance Characteristics

### Rate Limiting

- **Google Search**: 2-4s between results, 3-6s every 10 results
- **Website Crawling**: 3-7s between pages, 5-10s every 10 pages
- **MailboxLayer**: 1s between requests (API limit)

### Throughput

- **Without Enrichment**: ~10-15 leads/minute
- **With Enrichment (no verification)**: ~3-5 leads/minute
- **With Full Verification**: ~2-3 leads/minute

### Resource Usage

- **CPU**: Low (mostly I/O bound)
- **Memory**: ~100-200 MB per scraping job
- **Network**: ~1-5 MB/lead (depends on website size)

---

## Error Handling

### Graceful Degradation

```
If email verification fails:
    └─> Return best guess pattern

If leadership extraction fails:
    └─> Return company emails only

If website unreachable:
    └─> Skip lead, continue processing

If API quota exceeded:
    └─> Disable verification, continue scraping
```

### Retry Logic

- **HTTP requests**: 3 retries with exponential backoff
- **API calls**: 1 retry with 2s delay
- **Rate limit errors**: Extended backoff (up to 60s)

---

## Security Considerations

### API Keys

- Store in `.env` file (never commit)
- Use environment variables in production
- Rotate keys regularly

### Rate Limiting

- Respect robots.txt (when applicable)
- Use reasonable delays
- Avoid aggressive scraping

### Data Privacy

- GDPR compliance: Only scrape publicly available data
- CAN-SPAM compliance: Use verified emails responsibly
- Store data securely

---

## Scalability

### Horizontal Scaling

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Scraper    │     │  Scraper    │     │  Scraper    │
│  Instance 1 │     │  Instance 2 │     │  Instance 3 │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       └───────────────────┴───────────────────┘
                           │
                    ┌──────▼──────┐
                    │   Load      │
                    │  Balancer   │
                    └─────────────┘
```

### Optimization Tips

1. **Batch Processing**: Process 100 leads, save, repeat
2. **Parallel Workers**: Multiple instances with task queue
3. **Caching**: Cache verified emails (reduce API calls)
4. **Database**: Use PostgreSQL for large datasets

---

## Monitoring & Observability

### Key Metrics

- **Success Rate**: % of successfully enriched leads
- **Average Quality Score**: Mean quality score across leads
- **Verification Rate**: % of leads with verified emails
- **API Usage**: MailboxLayer quota consumption
- **Error Rate**: Failed requests / total requests

### Logging

```python
INFO: Enriching lead: https://company.com
INFO: ✓ Crawled 8 pages
INFO: ✓ Found 12 emails, 3 high-quality
INFO: ✓ Found 2 decision-makers
INFO: ✓ Verified email: john.doe@company.com
INFO: ✓ Quality Score: 85/100
```

---

## Future Enhancements

### Planned Features

- [ ] LinkedIn scraping integration
- [ ] Phone number verification
- [ ] Company size/revenue enrichment
- [ ] Social media profile linking
- [ ] Custom ML-based quality scoring
- [ ] Webhook notifications
- [ ] GraphQL API

### Community Contributions

See `CONTRIBUTING.md` for guidelines on:
- Adding new email pattern formats
- Supporting additional verification APIs
- Improving name extraction accuracy
- Adding new data sources

---

## License

MIT License - See `LICENSE` file for details.

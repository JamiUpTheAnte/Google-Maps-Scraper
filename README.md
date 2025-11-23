# Construction Company Lead Scraper

A robust Python-based lead generation tool that finds construction companies and their contact emails without getting IP banned. Designed for use with n8n automation or standalone execution.

## Features

### Anti-Ban Measures (Critical)
- **Random Delays**: 2-5 seconds between requests (configurable)
- **User Agent Rotation**: Cycles through 10 different browser user agents
- **Request Timeouts**: 10-second max timeout per request
- **Smart Rate Limiting**: 5-10 second delays between main site and contact pages
- **Failure Handling**: Skips and continues on errors (no immediate retries)
- **Safety Monitoring**: Warns at 5 consecutive failures, stops at 20

### Email Intelligence
- **Garbage Email Filtering**: Removes noreply@, no-reply@, abuse@, postmaster@, privacy@, support@, webmaster@
- **Email Validation**: Basic format checking for @ and domain
- **Domain Matching**: Prioritizes emails matching the company domain
- **Deduplication**: Automatic removal of duplicate emails per company

### Comprehensive Scraping
- **Multi-Page Scraping**: Visits main page + up to 2 contact pages
- **Contact Page Detection**: Finds /contact, /about, /contact-us, /reach-us, /get-in-touch pages
- **Company Name Extraction**: Extracts from page title or domain
- **JSON Export**: Pretty-printed JSON output with all lead data

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd Google-Maps-Scraper
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Run the scraper with default settings:
```bash
python scraper.py
```

The script will complete in **5-10 minutes** for 50 companies.

### Configuration

All settings are easily configurable at the top of `scraper.py`:

```python
# CONFIGURATION - Edit these values
SEARCH_QUERY = "construction company Atlanta"  # Your search query
MAX_RESULTS = 50                               # Max companies per run (default: 50)
MIN_DELAY = 2                                  # Min delay between requests (seconds)
MAX_DELAY = 5                                  # Max delay between requests (seconds)
CONTACT_PAGE_DELAY_MIN = 5                     # Delay before contact pages (seconds)
CONTACT_PAGE_DELAY_MAX = 10                    # Max delay before contact pages
REQUEST_TIMEOUT = 10                           # Request timeout (seconds)
OUTPUT_FILE = "leads.json"                     # Output filename
```

### Output Format

Results are saved to **leads.json** with the following structure:

```json
[
  {
    "company_name": "ABC Construction Company",
    "website": "https://example.com",
    "emails": [
      "contact@example.com",
      "info@example.com"
    ],
    "scraped_at": "2025-01-15T10:30:45.123456",
    "success": true
  }
]
```

### Summary Output

When complete, you'll see:
```
Found 35 companies with 67 total emails
Total companies processed: 50
Successfully scraped: 48
Failed: 2
```

## Architecture

The scraper is organized into clean, modular functions:

### Core Functions

- **`scrape_emails_from_url(url)`** - Scrapes emails from a single URL with error handling
- **`filter_garbage_emails(emails)`** - Removes unwanted email patterns
- **`find_contact_pages(soup, base_url)`** - Finds contact page URLs (up to 2)
- **`scrape_company(url)`** - Main scraping logic for one company
- **`main()`** - Orchestrates the entire scraping process

### Helper Functions

- **`validate_email(email)`** - Validates email format
- **`extract_domain(url)`** - Extracts domain from URL
- **`match_email_to_domain(emails, domain)`** - Prioritizes domain-matching emails

## Error Handling

All requests are wrapped in comprehensive try/except blocks:

- **`requests.exceptions.Timeout`** - Handles timeouts gracefully
- **`requests.exceptions.ConnectionError`** - Handles connection failures
- **`requests.exceptions.RequestException`** - Catches all request errors
- **Malformed HTML** - Handles missing titles and broken pages
- **Google search failures** - Returns empty results and continues

**Important**: The script does NOT retry failed requests immediately. It skips and continues to avoid triggering rate limits.

## Safety Features

### Consecutive Failure Tracking

The scraper monitors failures to detect potential IP bans:

- **Warning at 5 failures**: Alerts you to possible issues
- **Stops at 20 failures**: Automatically stops to prevent IP ban
- **Reset on success**: Consecutive counter resets when a request succeeds

Example warning output:
```
⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠
WARNING: 5 consecutive failures detected!
Possible IP ban or network issues.
⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠
```

## Best Practices

1. **Start Small**: Test with 10-20 results (edit `MAX_RESULTS`) before running large batches
2. **Monitor Output**: Watch console output for warnings and errors
3. **Use VPN/Proxy**: Consider using for large scraping jobs
4. **Respect Limits**: Don't increase `MAX_RESULTS` beyond 100 per session
5. **Adjust Delays**: If you get warnings, increase `MIN_DELAY` and `MAX_DELAY`
6. **Business Hours**: Run during off-peak hours when possible

## Troubleshooting

### Getting Blocked or Warnings?

1. Increase delays in configuration:
   ```python
   MIN_DELAY = 5
   MAX_DELAY = 10
   CONTACT_PAGE_DELAY_MIN = 10
   CONTACT_PAGE_DELAY_MAX = 15
   ```
2. Reduce `MAX_RESULTS` to 20-30
3. Use a VPN or proxy service
4. Wait 1-2 hours before retrying

### No Emails Found?

- Construction companies may not list emails publicly
- Try scraping more companies (`MAX_RESULTS`)
- Check that your search query is specific enough
- Some sites may require JavaScript (not supported by basic scraping)

### Google Search Not Working?

- Verify internet connection
- Try a different search query
- Check if you can search Google manually
- You may need to wait if temporarily rate-limited by Google

## Dependencies

Required Python packages (install via `pip install -r requirements.txt`):

- **`beautifulsoup4==4.12.2`** - HTML parsing
- **`requests==2.31.0`** - HTTP requests
- **`googlesearch-python==1.2.4`** - Google search functionality
- **`lxml==4.9.3`** - XML/HTML parser

Standard library (no installation needed):
- `time`, `random` - Delays and randomization
- `re` - Email pattern matching
- `json` - JSON output
- `datetime` - Timestamps
- `urllib.parse` - URL handling

## Integration with n8n

This scraper is designed to be callable from n8n automation workflows:

1. **Execute Command node**: Run `python scraper.py`
2. **Read Binary File node**: Read `leads.json`
3. **JSON Parse node**: Parse the results
4. **Split In Batches node**: Process emails in batches
5. **Send Email/CRM nodes**: Use the lead data

Example n8n workflow:
```
Trigger → Execute Command (python scraper.py) → Read File (leads.json) → Process Leads
```

## Legal & Ethical Considerations

⚠️ **Important Legal Notice**:

- **Respect Terms of Service**: Many websites prohibit automated scraping
- **Comply with robots.txt**: Check and respect robots.txt files
- **Data Privacy Laws**: Be aware of GDPR, CCPA, CAN-SPAM, and other regulations
- **Rate Limiting**: This tool includes rate limiting to avoid overloading servers
- **Intended Use**: For legitimate business development and lead generation only
- **No Spam**: Don't use scraped emails for unsolicited bulk email (spam)

**Users are solely responsible for ensuring their use complies with all applicable laws and website terms of service.**

## License

This tool is provided for educational and legitimate business purposes. The authors are not responsible for misuse.

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request with clear description

## Support

For issues or questions:
- Open an issue on GitHub
- Check the troubleshooting section above
- Review the configuration options

---

**Built with ❤️ for ethical lead generation**

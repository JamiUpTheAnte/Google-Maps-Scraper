# Construction Company Lead Scraper

**Safe, scalable Yelp-based lead generation tool for construction companies.**

## What It Does

1. **Searches Yelp** for construction companies/contractors by location
2. **Extracts business info** from Yelp: name, phone, website URL
3. **Scrapes websites** for emails and additional contact info
4. **Exports to CSV & JSON** for easy import into CRM

## Why Yelp Instead of Google?

✅ **No IP ban risk** - Yelp is more tolerant of scraping
✅ **Better data quality** - Verified businesses with phones
✅ **Scalable to 5K+ leads/month** - Can run repeatedly
✅ **Legal gray area but safer** - Not violating Google ToS

## Installation

```bash
pip install -r requirements.txt
```

Only 2 dependencies:
- `beautifulsoup4` - HTML parsing
- `requests` - HTTP requests

## Usage

### Basic Usage

```bash
python scraper.py
```

### Customize Search

Edit `scraper.py` line 421-424:

```python
CATEGORY = "general contractors"  # or "construction company", "home builders", etc.
LOCATION = "Atlanta, GA"          # any US city
NUM_RESULTS = 50                  # number of businesses to find
```

### Run Different Locations

For 5K leads/month, run multiple locations:

```bash
# Month 1: Major cities
python scraper.py  # Atlanta
# Edit LOCATION, run again
python scraper.py  # Miami
python scraper.py  # Dallas
# ... etc

# Month 2: Mid-size cities
python scraper.py  # Birmingham
python scraper.py  # Savannah
# ... etc
```

## Output Files

- `leads.csv` - Spreadsheet format (open in Excel/Google Sheets)
- `leads.json` - JSON format (import into CRM/database)
- `leads_partial.csv` - Auto-saved every 10 leads (backup)
- `scraper.log` - Detailed logs

## CSV Columns

| Column | Description |
|--------|-------------|
| website | Company website URL |
| company | Company name |
| emails | Email addresses (semicolon separated) |
| phones | Phone numbers (semicolon separated) |
| contact_pages | Contact page URLs found |
| scraped_at | Timestamp |
| status | success / failed / no_website |

## Scaling to 5K Leads/Month

### Strategy 1: Multiple Locations (Recommended)

Run 100-200 businesses per major city:
- 25 cities × 200 businesses = 5,000 leads
- Takes ~2 hours per city with rate limiting
- Spread across the month to avoid detection

**Top Construction Markets:**
- Atlanta, GA
- Dallas, TX
- Houston, TX
- Phoenix, AZ
- Las Vegas, NV
- Charlotte, NC
- Austin, TX
- Nashville, TN
- Denver, CO
- Miami, FL
- Tampa, FL
- Orlando, FL

### Strategy 2: Different Categories

Same location, different searches:
- "general contractors"
- "home builders"
- "remodeling contractors"
- "commercial construction"
- "roofing contractors"
- "concrete contractors"

### Strategy 3: Automate with Cron

**Linux/Mac:**
```bash
# Run daily at 2 AM
0 2 * * * cd /path/to/scraper && python scraper.py >> cron.log 2>&1
```

**Windows Task Scheduler:**
1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (daily, weekly, etc.)
4. Action: Start Program → python.exe
5. Arguments: scraper.py
6. Start in: C:\path\to\scraper

## Rate Limiting

Built-in protections to avoid IP bans:

- 3-7 seconds between requests
- Random delays to avoid patterns
- 5-10 second break every 10 requests
- Exponential backoff on errors
- User agent rotation

## Troubleshooting

### "No businesses found"

- Check LOCATION spelling (use "City, State" format)
- Try different CATEGORY keywords
- Yelp might have changed their HTML (see below)

### "Failed to fetch URL"

- Website is down or blocking scrapers
- Normal - skip and continue
- Check `scraper.log` for details

### Yelp HTML Changed

Yelp occasionally updates their site structure. If scraping stops working:

1. Open browser, search Yelp manually
2. Right-click → Inspect Element
3. Find business card HTML structure
4. Update `search_yelp()` function selectors

## Best Practices

1. **Don't run too frequently from same IP**
   - Max 500-1000 leads per day
   - Use different locations/categories
   - Take breaks between runs

2. **Use VPN for large volumes**
   - Rotate IPs when scraping 1000+ leads
   - Prevents Yelp rate limiting

3. **Keep data fresh**
   - Re-scrape locations every 6 months
   - Businesses close/change contact info

4. **Verify emails before sending**
   - Use email validation service
   - Avoid spam complaints

## Legal Disclaimer

This tool is for **educational purposes and lead research**.

- Yelp's ToS prohibits automated scraping
- Use at your own risk
- Don't abuse or overload their servers
- Respect robots.txt and rate limits
- Only use data for legitimate business purposes
- Comply with CAN-SPAM, GDPR, and local laws

For commercial use, consider:
- Yelp Fusion API (official, paid)
- Data broker services
- Manual research

## License

MIT License - Use freely, no warranty provided.

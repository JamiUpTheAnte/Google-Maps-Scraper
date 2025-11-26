# Google Maps Business Scraper

A Python-based web scraper with a Flask web interface and API that searches Google for businesses and extracts contact information including emails, phone numbers, and contact pages. Built with comprehensive rate limiting to avoid IP bans.

## Features

- **Web Interface**: Beautiful, user-friendly web interface for easy scraping
- **Flask API**: RESTful API endpoints for n8n and other automation tools
- **Configurable Search**: Change business type and location from the web interface
- **Real-time Progress**: Live progress tracking and status updates
- **Rate Limiting**: Built-in delays and exponential backoff to prevent IP bans
- **User Agent Rotation**: Randomly rotates user agents to appear more natural
- **Contact Information Extraction**: Automatically finds emails and phone numbers
- **Contact Page Detection**: Identifies and scrapes dedicated contact pages
- **Error Handling**: Robust retry logic with exponential backoff
- **Multiple Export Formats**: Download results as JSON or CSV
- **Command Line Support**: Can also be run as a standalone Python script

## Rate Limiting Features

The scraper includes multiple layers of rate limiting protection:

1. **Random Delays**: 3-7 seconds between each request (configurable)
2. **Extended Breaks**: Longer pauses every 10 requests
3. **Exponential Backoff**: Automatic retry with increasing delays on failures
4. **429 Handler**: Special handling for rate limit errors
5. **User Agent Rotation**: Cycles through 5 different user agents
6. **Checkpoint Saves**: Saves progress every 10 leads to avoid data loss

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

### Web Interface (Recommended)

1. Start the Flask web server:
```bash
python app.py
```

2. Open your web browser and navigate to:
```
http://localhost:5000
```

3. Use the web interface to:
   - Enter business type (e.g., "construction company", "restaurant", "dentist")
   - Enter location (e.g., "Atlanta", "New York", "Los Angeles")
   - Select number of results (10, 25, 50, or 100)
   - Adjust rate limiting settings if needed
   - Click "Start Scraping" and watch the progress in real-time
   - Download results as JSON or CSV when complete

### Command Line Usage

For automation or scripting, run the scraper directly:
```bash
python scraper.py
```

Edit the `main()` function in `scraper.py` to customize:

```python
# Configuration
QUERY = "construction company Atlanta"  # Change search query
NUM_RESULTS = 100                       # Number of results to scrape
MIN_DELAY = 3.0                         # Minimum delay (seconds)
MAX_DELAY = 7.0                         # Maximum delay (seconds)
```

### API Endpoints (for n8n Integration)

The Flask API provides the following endpoints:

**Start a scraping job:**
```bash
POST http://localhost:5000/api/scrape
Content-Type: application/json

{
  "business_type": "construction company",
  "location": "Atlanta",
  "num_results": 50,
  "min_delay": 3.0,
  "max_delay": 7.0
}
```

**Check scraping status:**
```bash
GET http://localhost:5000/api/status
```

**Get results:**
```bash
GET http://localhost:5000/api/results
```

**Download JSON:**
```bash
GET http://localhost:5000/api/download/json
```

**Download CSV:**
```bash
GET http://localhost:5000/api/download/csv
```

**Health check:**
```bash
GET http://localhost:5000/api/health
```

### Output Files

- `leads.csv` - Final results with all scraped data
- `results.json` - Results in JSON format
- `leads_partial.csv` - Checkpoint file updated every 10 leads
- `scraper.log` - Detailed log of all operations

### CSV Format

The output CSV includes:
- `website` - Company website URL
- `company` - Company name (from page title)
- `emails` - Email addresses found (semicolon-separated)
- `phones` - Phone numbers found (semicolon-separated)
- `contact_pages` - URLs of contact pages (semicolon-separated)
- `scraped_at` - Timestamp of when the data was collected
- `status` - Success or failure status

## n8n Integration

To use this scraper with n8n:

1. Start the Flask server: `python app.py`
2. In n8n, add an **HTTP Request** node
3. Configure the node:
   - **Method**: POST
   - **URL**: `http://localhost:5000/api/scrape`
   - **Body Content Type**: JSON
   - **Body Parameters**:
     ```json
     {
       "business_type": "restaurant",
       "location": "Miami",
       "num_results": 25,
       "min_delay": 3.0,
       "max_delay": 7.0
     }
     ```

4. Add a **Wait** node (wait 30-60 seconds for scraping to complete)
5. Add another **HTTP Request** node to get results:
   - **Method**: GET
   - **URL**: `http://localhost:5000/api/results`

6. Process the results in your n8n workflow

## Configuration Options

### Adjusting Rate Limiting

For more aggressive scraping (higher risk):
```python
scraper = RateLimitedScraper(
    min_delay=1.0,    # Faster requests
    max_delay=3.0,
    request_timeout=10
)
```

For more conservative scraping (safer):
```python
scraper = RateLimitedScraper(
    min_delay=5.0,    # Slower, safer
    max_delay=10.0,
    request_timeout=15
)
```

### Search Parameters

The Google search uses these parameters:
- `pause=2.0` - Built-in delay between search requests
- Additional 3-6 second break every 10 results

## Best Practices

1. **Start Small**: Test with 10-20 results before running large batches
2. **Monitor Logs**: Watch `scraper.log` for rate limit warnings
3. **Use VPN**: Consider using a VPN for large scraping jobs
4. **Respect robots.txt**: Be aware of website terms of service
5. **Adjust Delays**: If you get blocked, increase `MIN_DELAY` and `MAX_DELAY`

## Troubleshooting

### Getting Blocked?

- Increase `MIN_DELAY` and `MAX_DELAY` values
- Reduce `NUM_RESULTS` per session
- Use a VPN or proxy
- Add more breaks between requests

### Low Success Rate?

- Check `scraper.log` for specific errors
- Some sites may block automated access
- Increase `request_timeout` for slow sites
- Verify your internet connection

### No Results Found?

- Check if Google search returns results manually
- Try a different search query
- Verify dependencies are installed correctly

## Dependencies

- `beautifulsoup4` - HTML parsing
- `requests` - HTTP requests
- `googlesearch-python` - Google search API
- `lxml` - XML/HTML parser

## Legal & Ethical Considerations

- Respect website terms of service
- Comply with robots.txt files
- Use scraped data responsibly
- Be aware of data privacy laws (GDPR, CCPA, etc.)
- Avoid overloading servers with requests

## License

This tool is for educational purposes. Users are responsible for ensuring their use complies with applicable laws and website terms of service.

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## Support

For issues or questions, please open an issue on GitHub.

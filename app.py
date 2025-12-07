"""
Flask Web Application for Google Maps Business Scraper
Provides web interface and API endpoints for n8n integration
Enhanced with lead enrichment, email verification, and decision-maker extraction
"""

from flask import Flask, render_template, request, jsonify, send_file
from scraper import RateLimitedScraper, save_to_csv
from google_maps_scraper import search_google_maps
import json
import os
from datetime import datetime
import threading
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables to store scraping state
current_results = []
scraping_status = {
    'is_running': False,
    'progress': 0,
    'total': 0,
    'status': 'idle',
    'message': 'Ready to start scraping',
    'last_run': None
}


def run_scraping_job(business_type, location, num_results, min_delay, max_delay,
                     enable_enrichment=False, mailbox_api_key=None, headless=False):
    """Run scraping in background"""
    global current_results, scraping_status

    try:
        scraping_status['is_running'] = True
        scraping_status['status'] = 'running'
        scraping_status['message'] = 'Searching Google...'
        scraping_status['progress'] = 0

        logger.info(f"Starting scrape: {business_type} in {location}")
        logger.info(f"Enrichment enabled: {enable_enrichment}")
        logger.info(f"Headless mode: {headless}")

        # Search Google Maps with Selenium (opens Chrome browser)
        mode_text = "background" if headless else "visible window"
        scraping_status['message'] = f'Opening Chrome ({mode_text}) and searching Google Maps...'
        businesses = search_google_maps(business_type, location, num_results, headless=headless)

        scraping_status['total'] = len(businesses)

        if not businesses:
            scraping_status['status'] = 'error'
            scraping_status['message'] = 'No businesses found on Google Maps'
            scraping_status['is_running'] = False
            return

        logger.info(f"Found {len(businesses)} businesses on Google Maps")
        scraping_status['message'] = f'Found {len(businesses)} businesses. Starting website scraping...'

        # Initialize scraper with enrichment support
        scraper = RateLimitedScraper(
            min_delay=min_delay,
            max_delay=max_delay,
            request_timeout=10,
            enable_enrichment=enable_enrichment,
            mailbox_api_key=mailbox_api_key
        )

        # Scrape each business website
        current_results = []
        for i, business in enumerate(businesses, 1):
            scraping_status['progress'] = i

            # Start with Google Maps data
            lead = {
                'name': business.get('name', ''),
                'phone': business.get('phone', ''),
                'address': business.get('address', ''),
                'rating': business.get('rating', ''),
                'reviews': business.get('reviews', ''),
                'category': business.get('category', ''),
                'website': business.get('website', ''),
                'source': 'google_maps'
            }

            # If website exists, enrich with website scraping
            if business.get('website'):
                url = business['website']
                scraping_status['message'] = f'Enriching {i}/{len(businesses)}: {url[:50]}...'
                logger.info(f"[{i}/{len(businesses)}] Enriching: {url}")

                try:
                    enriched = scraper.scrape_website(
                        url,
                        company=business.get('name'),
                        phone=business.get('phone'),
                        location=location
                    )
                    # Merge enriched data with Google Maps data
                    lead.update(enriched)
                except Exception as e:
                    logger.error(f"Error enriching {url}: {e}")
                    lead['status'] = 'partial'  # Has Google Maps data but enrichment failed
            else:
                logger.info(f"[{i}/{len(businesses)}] No website for: {business.get('name')}")
                lead['status'] = 'no_website'

            current_results.append(lead)

            # Save checkpoint every 10 leads
            if i % 10 == 0:
                save_results_to_files()

        # Save final results
        save_results_to_files()

        # Update status
        successful = sum(1 for lead in current_results if lead['status'] == 'success')

        # Calculate enrichment stats if enabled
        if enable_enrichment:
            with_decision_makers = sum(1 for lead in current_results
                                      if lead.get('decision_makers', []))
            with_verified = sum(1 for lead in current_results
                               if lead.get('has_verified_emails', False))
            avg_quality = sum(lead.get('quality_score', 0) for lead in current_results) / len(current_results)

            scraping_status['message'] = (
                f'Completed! {successful}/{len(current_results)} successful leads. '
                f'{with_decision_makers} with decision-makers, '
                f'{with_verified} with verified emails. '
                f'Avg quality: {avg_quality:.1f}/100'
            )
        else:
            scraping_status['message'] = f'Completed! Found {successful}/{len(current_results)} successful leads'

        scraping_status['status'] = 'completed'
        scraping_status['last_run'] = datetime.now().isoformat()
        scraping_status['is_running'] = False

        logger.info("Scraping job completed successfully")

    except Exception as e:
        logger.error(f"Error in scraping job: {e}", exc_info=True)
        scraping_status['status'] = 'error'
        scraping_status['message'] = f'Error: {str(e)}'
        scraping_status['is_running'] = False


def save_results_to_files():
    """Save current results to JSON and CSV files"""
    global current_results

    # Save JSON
    with open('results.json', 'w', encoding='utf-8') as f:
        json.dump(current_results, f, indent=2)

    # Save CSV
    save_to_csv(current_results, 'leads.csv')


@app.route('/')
def index():
    """Serve the main web interface"""
    return render_template('index.html')


@app.route('/api/scrape', methods=['POST'])
def start_scrape():
    """
    API endpoint to start a scraping job
    Expected JSON body:
    {
        "business_type": "construction company",
        "location": "Atlanta",
        "num_results": 50,
        "min_delay": 3.0,
        "max_delay": 7.0,
        "enable_enrichment": true,
        "mailbox_api_key": "your_mailboxlayer_api_key"
    }
    """
    if scraping_status['is_running']:
        return jsonify({
            'success': False,
            'message': 'Scraping job already running'
        }), 400

    data = request.json
    business_type = data.get('business_type', 'construction company')
    location = data.get('location', 'Atlanta')
    num_results = int(data.get('num_results', 50))
    min_delay = float(data.get('min_delay', 3.0))
    max_delay = float(data.get('max_delay', 7.0))

    # Enrichment parameters
    enable_enrichment = data.get('enable_enrichment', False)
    mailbox_api_key = data.get('mailbox_api_key') or os.getenv('MAILBOXLAYER_API_KEY')

    # Performance parameters
    headless = data.get('headless', False)  # Default to visible Chrome window

    # Start scraping in background thread
    thread = threading.Thread(
        target=run_scraping_job,
        args=(business_type, location, num_results, min_delay, max_delay,
              enable_enrichment, mailbox_api_key, headless)
    )
    thread.daemon = True
    thread.start()

    return jsonify({
        'success': True,
        'message': 'Scraping job started',
        'query': f"{business_type} {location}",
        'enrichment_enabled': enable_enrichment
    })


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current scraping status"""
    return jsonify(scraping_status)


@app.route('/api/results', methods=['GET'])
def get_results():
    """Get current scraping results"""
    return jsonify({
        'success': True,
        'count': len(current_results),
        'results': current_results
    })


@app.route('/api/download/json', methods=['GET'])
def download_json():
    """Download results as JSON file"""
    if not current_results:
        return jsonify({'success': False, 'message': 'No results available'}), 404

    # Ensure file is saved
    save_results_to_files()

    return send_file(
        'results.json',
        mimetype='application/json',
        as_attachment=True,
        download_name=f'leads_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    )


@app.route('/api/download/csv', methods=['GET'])
def download_csv():
    """Download results as CSV file"""
    if not current_results:
        return jsonify({'success': False, 'message': 'No results available'}), 404

    # Ensure file is saved
    save_results_to_files()

    return send_file(
        'leads.csv',
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'leads_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })


if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)

    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)

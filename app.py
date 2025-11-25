"""
Flask API for Yelp Business Lead Scraper
Provides web interface and REST API for n8n integration
"""

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import threading
import uuid
import os
from datetime import datetime
from scraper import run_scraper
import logging

app = Flask(__name__)
CORS(app)  # Enable CORS for n8n integration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# In-memory job storage (use Redis/database for production)
jobs = {}
job_lock = threading.Lock()


def run_scraper_job(job_id, category, location, num_results):
    """Run scraper in background thread"""
    try:
        with job_lock:
            jobs[job_id]['status'] = 'running'
            jobs[job_id]['started_at'] = datetime.now().isoformat()

        logger.info(f"Starting scraper job {job_id}: {category} in {location}")

        # Run the scraper
        output_prefix = f"results/{job_id}"
        os.makedirs('results', exist_ok=True)

        result = run_scraper(
            category=category,
            location=location,
            num_results=num_results,
            output_prefix=output_prefix
        )

        # Update job status
        with job_lock:
            jobs[job_id]['status'] = 'completed'
            jobs[job_id]['completed_at'] = datetime.now().isoformat()
            jobs[job_id]['result'] = result
            jobs[job_id]['error'] = None

        logger.info(f"Completed scraper job {job_id}")

    except Exception as e:
        logger.error(f"Error in scraper job {job_id}: {e}")
        with job_lock:
            jobs[job_id]['status'] = 'failed'
            jobs[job_id]['completed_at'] = datetime.now().isoformat()
            jobs[job_id]['error'] = str(e)


# ============================================================================
# WEB INTERFACE ROUTES
# ============================================================================

@app.route('/')
def index():
    """Render main web interface"""
    return render_template('index.html')


@app.route('/jobs')
def jobs_page():
    """Render jobs list page"""
    return render_template('jobs.html', jobs=jobs)


# ============================================================================
# API ROUTES (for n8n and programmatic access)
# ============================================================================

@app.route('/api/scrape', methods=['POST'])
def api_scrape():
    """
    Start a new scraping job

    POST /api/scrape
    Body: {
        "category": "general contractors",
        "location": "Atlanta, GA",
        "num_results": 50
    }

    Returns: {
        "job_id": "uuid",
        "status": "queued",
        "message": "Job created successfully"
    }
    """
    try:
        data = request.get_json()

        # Validate input
        category = data.get('category', 'general contractors')
        location = data.get('location', 'Atlanta, GA')
        num_results = int(data.get('num_results', 50))

        if not category or not location:
            return jsonify({
                'success': False,
                'error': 'Category and location are required'
            }), 400

        if num_results < 1 or num_results > 100:
            return jsonify({
                'success': False,
                'error': 'num_results must be between 1 and 100'
            }), 400

        # Create job
        job_id = str(uuid.uuid4())
        with job_lock:
            jobs[job_id] = {
                'job_id': job_id,
                'status': 'queued',
                'category': category,
                'location': location,
                'num_results': num_results,
                'created_at': datetime.now().isoformat(),
                'started_at': None,
                'completed_at': None,
                'result': None,
                'error': None
            }

        # Start scraper in background thread
        thread = threading.Thread(
            target=run_scraper_job,
            args=(job_id, category, location, num_results)
        )
        thread.daemon = True
        thread.start()

        logger.info(f"Created job {job_id}: {category} in {location}")

        return jsonify({
            'success': True,
            'job_id': job_id,
            'status': 'queued',
            'message': 'Job created successfully',
            'check_status_url': f'/api/status/{job_id}'
        }), 202

    except Exception as e:
        logger.error(f"Error creating job: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/status/<job_id>', methods=['GET'])
def api_status(job_id):
    """
    Check status of a scraping job

    GET /api/status/<job_id>

    Returns: {
        "job_id": "uuid",
        "status": "running|completed|failed",
        "category": "...",
        "location": "...",
        "created_at": "...",
        "started_at": "...",
        "completed_at": "...",
        "stats": {...}
    }
    """
    with job_lock:
        job = jobs.get(job_id)

    if not job:
        return jsonify({
            'success': False,
            'error': 'Job not found'
        }), 404

    response = {
        'success': True,
        'job_id': job['job_id'],
        'status': job['status'],
        'category': job['category'],
        'location': job['location'],
        'num_results': job['num_results'],
        'created_at': job['created_at'],
        'started_at': job['started_at'],
        'completed_at': job['completed_at']
    }

    # Add results if completed
    if job['status'] == 'completed' and job['result']:
        response['stats'] = job['result']['stats']
        response['files'] = job['result']['files']
        response['download_csv_url'] = f'/api/download/{job_id}/csv'
        response['download_json_url'] = f'/api/download/{job_id}/json'

    # Add error if failed
    if job['status'] == 'failed':
        response['error'] = job['error']

    return jsonify(response)


@app.route('/api/results/<job_id>', methods=['GET'])
def api_results(job_id):
    """
    Get full results of a completed job

    GET /api/results/<job_id>

    Returns: {
        "success": true,
        "job_id": "...",
        "leads": [...],
        "stats": {...}
    }
    """
    with job_lock:
        job = jobs.get(job_id)

    if not job:
        return jsonify({
            'success': False,
            'error': 'Job not found'
        }), 404

    if job['status'] != 'completed':
        return jsonify({
            'success': False,
            'error': f'Job is {job["status"]}, not completed'
        }), 400

    return jsonify({
        'success': True,
        'job_id': job_id,
        'leads': job['result']['leads'],
        'stats': job['result']['stats'],
        'search_params': job['result']['search_params']
    })


@app.route('/api/download/<job_id>/<format>', methods=['GET'])
def api_download(job_id, format):
    """
    Download results file (CSV or JSON)

    GET /api/download/<job_id>/csv
    GET /api/download/<job_id>/json
    """
    with job_lock:
        job = jobs.get(job_id)

    if not job:
        return jsonify({
            'success': False,
            'error': 'Job not found'
        }), 404

    if job['status'] != 'completed':
        return jsonify({
            'success': False,
            'error': f'Job is {job["status"]}, not completed'
        }), 400

    # Get file path
    if format == 'csv':
        file_path = job['result']['files']['csv']
        mimetype = 'text/csv'
    elif format == 'json':
        file_path = job['result']['files']['json']
        mimetype = 'application/json'
    else:
        return jsonify({
            'success': False,
            'error': 'Invalid format. Use csv or json'
        }), 400

    if not os.path.exists(file_path):
        return jsonify({
            'success': False,
            'error': 'File not found'
        }), 404

    return send_file(
        file_path,
        mimetype=mimetype,
        as_attachment=True,
        download_name=os.path.basename(file_path)
    )


@app.route('/api/jobs', methods=['GET'])
def api_jobs():
    """
    List all jobs

    GET /api/jobs?status=completed&limit=10

    Returns: {
        "success": true,
        "jobs": [...]
    }
    """
    status_filter = request.args.get('status')
    limit = int(request.args.get('limit', 100))

    with job_lock:
        job_list = list(jobs.values())

    # Filter by status if specified
    if status_filter:
        job_list = [j for j in job_list if j['status'] == status_filter]

    # Sort by created_at descending
    job_list.sort(key=lambda x: x['created_at'], reverse=True)

    # Limit results
    job_list = job_list[:limit]

    # Remove large result data from list view
    for job in job_list:
        job_copy = job.copy()
        if 'result' in job_copy and job_copy['result']:
            job_copy['result'] = {
                'stats': job_copy['result'].get('stats', {}),
                'files': job_copy['result'].get('files', {})
            }

    return jsonify({
        'success': True,
        'count': len(job_list),
        'jobs': job_list
    })


@app.route('/api/health', methods=['GET'])
def api_health():
    """Health check endpoint"""
    return jsonify({
        'success': True,
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Not found'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500


if __name__ == '__main__':
    # Create results directory
    os.makedirs('results', exist_ok=True)

    logger.info("=" * 70)
    logger.info("YELP LEAD SCRAPER API")
    logger.info("=" * 70)
    logger.info("Web Interface: http://localhost:5000")
    logger.info("API Endpoint: http://localhost:5000/api/scrape")
    logger.info("API Docs: See README.md")
    logger.info("=" * 70)

    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)

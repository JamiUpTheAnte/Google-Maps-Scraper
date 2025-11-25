# Yelp Lead Scraper API Documentation

## Overview

The Yelp Lead Scraper provides a REST API that can be integrated with n8n and other automation tools.

**Base URL:** `http://localhost:5000` (or your server URL)

---

## Quick Start

### 1. Start the API Server

```bash
python app.py
```

The server will start on `http://localhost:5000`

### 2. Access Web Interface

Open your browser to `http://localhost:5000` to use the web interface.

---

## API Endpoints

### 1. Start a Scraping Job

**Endpoint:** `POST /api/scrape`

Start a new scraping job with custom search criteria.

**Request Body:**
```json
{
  "category": "general contractors",
  "location": "Atlanta, GA",
  "num_results": 50
}
```

**Parameters:**
- `category` (string, required): Business category to search (e.g., "plumbers", "electricians", "roofers")
- `location` (string, required): City and state (e.g., "New York, NY", "Los Angeles, CA")
- `num_results` (integer, optional): Number of businesses to scrape (1-100, default: 50)

**Response:** `202 Accepted`
```json
{
  "success": true,
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "queued",
  "message": "Job created successfully",
  "check_status_url": "/api/status/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**Example cURL:**
```bash
curl -X POST http://localhost:5000/api/scrape \
  -H "Content-Type: application/json" \
  -d '{"category": "plumbers", "location": "Dallas, TX", "num_results": 25}'
```

---

### 2. Check Job Status

**Endpoint:** `GET /api/status/{job_id}`

Check the status of a running or completed job.

**Response:**
```json
{
  "success": true,
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "completed",
  "category": "plumbers",
  "location": "Dallas, TX",
  "num_results": 25,
  "created_at": "2024-11-23T10:30:00",
  "started_at": "2024-11-23T10:30:05",
  "completed_at": "2024-11-23T10:45:00",
  "stats": {
    "total": 25,
    "with_websites": 20,
    "with_emails": 15,
    "with_phones": 22,
    "successful": 20
  },
  "files": {
    "csv": "results/a1b2c3d4-e5f6-7890-abcd-ef1234567890.csv",
    "json": "results/a1b2c3d4-e5f6-7890-abcd-ef1234567890.json"
  },
  "download_csv_url": "/api/download/a1b2c3d4-e5f6-7890-abcd-ef1234567890/csv",
  "download_json_url": "/api/download/a1b2c3d4-e5f6-7890-abcd-ef1234567890/json"
}
```

**Status Values:**
- `queued`: Job is waiting to start
- `running`: Job is currently scraping
- `completed`: Job finished successfully
- `failed`: Job encountered an error

**Example cURL:**
```bash
curl http://localhost:5000/api/status/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

---

### 3. Get Full Results

**Endpoint:** `GET /api/results/{job_id}`

Get the complete results including all lead data.

**Response:**
```json
{
  "success": true,
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "leads": [
    {
      "company": "ABC Plumbing",
      "website": "https://abcplumbing.com",
      "emails": ["contact@abcplumbing.com", "info@abcplumbing.com"],
      "phones": ["(555) 123-4567"],
      "contact_pages": ["https://abcplumbing.com/contact"],
      "scraped_at": "2024-11-23T10:35:00",
      "status": "success"
    },
    ...
  ],
  "stats": {
    "total": 25,
    "with_websites": 20,
    "with_emails": 15,
    "with_phones": 22,
    "successful": 20
  },
  "search_params": {
    "category": "plumbers",
    "location": "Dallas, TX",
    "num_results": 25
  }
}
```

**Example cURL:**
```bash
curl http://localhost:5000/api/results/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

---

### 4. Download Results File

**Endpoint:** `GET /api/download/{job_id}/{format}`

Download results as CSV or JSON file.

**Parameters:**
- `format`: Either `csv` or `json`

**Example:**
```
GET /api/download/a1b2c3d4-e5f6-7890-abcd-ef1234567890/csv
GET /api/download/a1b2c3d4-e5f6-7890-abcd-ef1234567890/json
```

**Example cURL:**
```bash
# Download CSV
curl -O http://localhost:5000/api/download/a1b2c3d4-e5f6-7890-abcd-ef1234567890/csv

# Download JSON
curl -O http://localhost:5000/api/download/a1b2c3d4-e5f6-7890-abcd-ef1234567890/json
```

---

### 5. List All Jobs

**Endpoint:** `GET /api/jobs`

List all scraping jobs with optional filtering.

**Query Parameters:**
- `status` (optional): Filter by status (`queued`, `running`, `completed`, `failed`)
- `limit` (optional): Maximum number of jobs to return (default: 100)

**Response:**
```json
{
  "success": true,
  "count": 5,
  "jobs": [
    {
      "job_id": "...",
      "status": "completed",
      "category": "plumbers",
      "location": "Dallas, TX",
      "num_results": 25,
      "created_at": "2024-11-23T10:30:00",
      "result": {
        "stats": {...},
        "files": {...}
      }
    },
    ...
  ]
}
```

**Example cURL:**
```bash
# Get all jobs
curl http://localhost:5000/api/jobs

# Get only completed jobs
curl http://localhost:5000/api/jobs?status=completed

# Get last 10 jobs
curl http://localhost:5000/api/jobs?limit=10
```

---

### 6. Health Check

**Endpoint:** `GET /api/health`

Check if the API is running.

**Response:**
```json
{
  "success": true,
  "status": "healthy",
  "timestamp": "2024-11-23T10:30:00"
}
```

---

## n8n Integration Guide

### Workflow Setup

Here's how to integrate the scraper with n8n:

#### Step 1: Create HTTP Request Node (Start Job)

1. Add an **HTTP Request** node
2. Configure:
   - **Method:** POST
   - **URL:** `http://localhost:5000/api/scrape`
   - **Authentication:** None
   - **Body Content Type:** JSON
   - **Specify Body:** Using Fields Below
   - **Fields:**
     - `category`: `{{ $json.category }}`
     - `location`: `{{ $json.location }}`
     - `num_results`: `{{ $json.num_results }}`

This will return a `job_id` that you'll use in the next step.

#### Step 2: Add Wait Node (Optional)

Add a **Wait** node to give the job time to complete:
- **Resume:** After Time Interval
- **Interval:** 30 seconds (adjust based on job size)

#### Step 3: Check Job Status

Add another **HTTP Request** node:
- **Method:** GET
- **URL:** `http://localhost:5000/api/status/{{ $json.job_id }}`

This returns the job status and statistics.

#### Step 4: Get Results (If Completed)

Add a **Switch** node to check if status is "completed":
- **Mode:** Rules
- **Rule:** `{{ $json.status }}` equals `completed`

If completed, add an **HTTP Request** node:
- **Method:** GET
- **URL:** `http://localhost:5000/api/results/{{ $json.job_id }}`

This returns all the leads data.

#### Step 5: Process Results

Add whatever processing you need:
- **Split Into Items** node to process each lead
- **Email** node to send notifications
- **Spreadsheet** node to save to Google Sheets
- **CRM** node to add leads to your CRM

### Example n8n Workflow (JSON)

```json
{
  "nodes": [
    {
      "parameters": {
        "method": "POST",
        "url": "http://localhost:5000/api/scrape",
        "jsonParameters": true,
        "options": {},
        "bodyParametersJson": "={\n  \"category\": \"{{ $json.category }}\",\n  \"location\": \"{{ $json.location }}\",\n  \"num_results\": {{ $json.num_results }}\n}"
      },
      "name": "Start Scraping Job",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 1,
      "position": [250, 300]
    },
    {
      "parameters": {
        "amount": 30
      },
      "name": "Wait 30s",
      "type": "n8n-nodes-base.wait",
      "typeVersion": 1,
      "position": [450, 300],
      "webhookId": "auto-generated"
    },
    {
      "parameters": {
        "url": "=http://localhost:5000/api/status/{{ $json.job_id }}"
      },
      "name": "Check Status",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 1,
      "position": [650, 300]
    },
    {
      "parameters": {
        "url": "=http://localhost:5000/api/results/{{ $json.job_id }}"
      },
      "name": "Get Results",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 1,
      "position": [850, 300]
    }
  ]
}
```

### Triggering from n8n

You can trigger scraping jobs from n8n in several ways:

1. **Schedule:** Use a **Cron** node to run daily/weekly
2. **Webhook:** Trigger via webhook from external systems
3. **Manual:** Click "Execute Workflow" button
4. **Form:** Use an n8n Form to collect category/location input

---

## Error Handling

### Error Responses

All errors return appropriate HTTP status codes:

**400 Bad Request:**
```json
{
  "success": false,
  "error": "Category and location are required"
}
```

**404 Not Found:**
```json
{
  "success": false,
  "error": "Job not found"
}
```

**500 Internal Server Error:**
```json
{
  "success": false,
  "error": "Internal server error"
}
```

### Retry Logic

For production use, implement retry logic in n8n:
1. Check status every 10-30 seconds
2. Set maximum retries (e.g., 20 attempts = 10 minutes)
3. Handle timeout gracefully

---

## Rate Limiting

The scraper includes built-in rate limiting:
- **Between Yelp pages:** 3-6 seconds
- **Between business pages:** 2-4 seconds
- **Between website scrapes:** 3-7 seconds (configurable)

This prevents IP bans and respects server resources.

---

## Production Deployment

### Security Recommendations

1. **Add Authentication:**
   - Use API keys or JWT tokens
   - Add rate limiting per API key
   - Implement HTTPS

2. **Use a Real Database:**
   - Replace in-memory job storage with PostgreSQL/MongoDB
   - Persist jobs across server restarts

3. **Add Queue System:**
   - Use Celery + Redis for better job management
   - Handle concurrent jobs properly

4. **Environment Variables:**
   - Store API keys and secrets in `.env` file
   - Configure base URL dynamically

### Docker Deployment

Create a `Dockerfile`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

Build and run:
```bash
docker build -t yelp-scraper-api .
docker run -p 5000:5000 yelp-scraper-api
```

---

## Support

For questions or issues:
- Check the logs in `scraper.log`
- Review the `/api/health` endpoint
- Ensure Chrome/ChromeDriver is installed properly

---

## License

MIT License - See LICENSE file for details

Automated Outreach Pipeline (B2B Lead Enrichment & Outreach System)

A production-grade, modular B2B sales automation tool built in Python. Starting from a single seed company domain, the pipeline automates finding lookalike companies, extracting executive profiles, resolving verified email addresses, and launching personalized outreach campaigns.

Architecture & File Directory

outreach-pipeline/
│
├── main.py                # Main entry-point script (User Interaction & Stage Orchestration)
├── config.py              # Centralized environment variable & dynamic config loader
├── requirements.txt       # Project python dependencies
├── .env                   # Local API key configurations (ignored in git)
├── .env.template          # Variable guide for local setups
│
├── services/
│   ├── ocean_service.py       # Stage 1: Similar business discovery via Ocean.io
│   ├── prospeo_service.py     # Stage 2: Lead prospecting & contacts extraction via Prospeo
│   ├── eazyreach_service.py   # Stage 3: LinkedIn URL-to-email resolution via Eazyreach
│   └── brevo_service.py       # Stage 4: Dynamic cold outreach templates via Brevo SMTP
│
├── data/
│   ├── companies.csv          # Lookalike companies database
│   ├── contacts.csv           # Lead profile contact data
│   └── emails.csv             # Verified email database
│
├── logs/
│   └── app.log                # Standard operational audit & failure logs
│
└── utils/
    ├── logger.py              # Global double-output logger initialization
    └── helpers.py             # Validation helper utilities and retry decorators


Stage Integration Specifications

Stage 1: Ocean.io Lookalike Lookup

* Action: Given a target seed domain, find lookalikes.
* Endpoint: POST https://api.ocean.io/v2/lookalike/companies/search
* Headers: X-Api-Token: OCEAN_API_KEY
* JSON Payload:{
*   "size": 10,
*   "fields": ["domain", "name"],
*   "companiesFilters": {
*     "seedDomains": ["hubspot.com"]
*   }
* }  
* Output: Writes details to data/companies.csv.
Stage 2: Prospeo Decision Maker Lookup

* Action: Finds C-level and VP prospects at target domains.
* Endpoint: POST https://api.prospeo.io/search-person
* Headers: X-KEY: PROSPEO_API_KEY
* JSON Payload:{
*   "page": 1,
*   "filters": {
*     "company_domain": { "include": ["domain.com"] },
*     "person_job_title": {
*       "include": ["CEO", "CTO", "CFO", "COO", "VP", "VP of Sales", "VP of Marketing", "Vice President", "Chief", "President", "Founder", "Director"]
*     }
*   }
* }  
* Output: Writes details to data/contacts.csv.
Stage 3: Eazyreach Email Resolution

* Action: Resolves verified business emails from LinkedIn profiles.
* Endpoint: POST https://api.eazyreach.app/v1/resolve
* Headers: Authorization: Bearer EAZYREACH_API_KEY
* JSON Payload:{
*   "linkedin_url": "https://www.linkedin.com/in/prospect-username"
* }  
* Output: Validates formatting, deduplicates, and writes to data/emails.csv.
Stage 4: Brevo dynamic cold outreach

* Action: Personalizes and sends B2B prospecting emails.
* Endpoint: POST https://api.brevo.com/v3/smtp/email
* Headers: api-key: BREVO_API_KEY
* JSON Payload:{
*   "sender": { "name": "Sender Name", "email": "sender@domain.com" },
*   "to": [{ "email": "recipient@domain.com", "name": "Full Name" }],
*   "subject": "Quick idea for CompanyName",
*   "textContent": "Hi FirstName, ...",
*   "htmlContent": "<html><body>Hi FirstName, ...</body></html>"
* }  

Production Reliability Design

1. Exponential Backoff Retries: All HTTP requests are decorated with a retry wrapper that sleeps and backs off exponentially on transient HTTP errors (e.g. 500, 502, 503, 504).
2. Rate Limit Management: The network retry wrapper parses 429 Too Many Requests status codes and extracts the standard HTTP Retry-After header to block execution for the requested duration.
3. Graceful Fallback Mode: When API credentials in .env are missing or set to placeholder values, the application runs using logical, domain-driven mock structures. This allows test runs and code evaluation out-of-the-box.
4. Data Deduplication: Prevents contacting the same email address twice by running cross-checks against previously recorded rows in CSV outputs.

Setup & Running Locally

1. Requirements Setup

Ensure Python 3.9+ is installed, then install project dependencies:
source .venv/bin/activate 

pip install -r requirements.txt

2. Configure Environment variables

Copy the template configuration and input your API keys:
cp .env.template .env

Open .env and fill out your specific credentials. If keys are missing, mock fallback data will be injected automatically.
3. Run Pipeline CLI

Start the application runner:
python app.py 

all over run 1 command -  
 .venv/bin/python app.py


Personalization Email Template

Dynamic tags ({{first_name}}, {{company}}, {{job_title}}, {{sender_name}}) are resolved and formatted per prospect:
Subject:
Quick idea for {{company}}

Body:
Hi {{first_name}},

I came across {{company}} and noticed your role as {{job_title}}.

We help companies improve outreach automation and lead generation through AI-powered workflows.

Would you be open to a quick discussion?

Regards,
{{sender_name}}

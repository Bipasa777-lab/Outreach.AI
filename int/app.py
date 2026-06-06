import os
import pandas as pd
# Dynamic web routing dashboard imports
from flask import Flask, render_template, request, jsonify
from config import Config
from utils.logger import logger
from utils.helpers import is_valid_domain, clean_domain
from services.ocean_service import OceanService
from services.prospeo_service import ProspeoService
from services.eazyreach_service import EazyreachService
from services.brevo_service import BrevoService

app = Flask(__name__)

# Initialize application directories
Config.ensure_directories()

@app.route("/")
def index():
    """Serves the central dashboard index html view."""
    missing_creds = Config.get_missing_credentials()
    return render_template("index.html", missing_creds=missing_creds)

@app.route("/api/run-stages-1-3", methods=["POST"])
def run_stages_1_3():
    """Triggers the lookup stages (Ocean.io -> Prospeo -> Eazyreach) to fetch verified lead profiles."""
    try:
        payload = request.json or {}
        raw_domain = payload.get("domain", "").strip()
        
        if not raw_domain:
            return jsonify({"success": False, "error": "Domain field is required."}), 400
            
        if not is_valid_domain(raw_domain):
            return jsonify({"success": False, "error": f"Invalid domain: '{raw_domain}'. Enter standard format (e.g. hubspot.com)."}), 400
            
        cleaned_domain = clean_domain(raw_domain)
        logger.info(f"Web API: Initializing stages 1-3 pipeline for domain: {cleaned_domain}")
        
        # Stage 1: Ocean.io lookalike competitor matching
        lookalikes = OceanService.get_lookalike_companies(cleaned_domain)
        if not lookalikes:
            return jsonify({"success": False, "error": "No matching lookalike company domains discovered."}), 404
            
        # Stage 2: Prospeo decision maker prospecting
        contacts = ProspeoService.find_decision_makers(lookalikes)
        if not contacts:
            return jsonify({"success": False, "error": "No C-level or VP contacts resolved for lookalike domains."}), 404
            
        # Stage 3: Eazyreach email resolving
        emails = EazyreachService.resolve_emails(contacts)
        if not emails:
            return jsonify({"success": False, "error": "No verified work emails resolved from executive list."}), 404
            
        return jsonify({
            "success": True,
            "companies": lookalikes,
            "contacts": contacts,
            "emails": emails
        })
        
    except Exception as e:
        logger.error(f"Web API Stages 1-3 pipeline failure: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/run-stage-4", methods=["POST"])
def run_stage_4():
    """Triggers Stage 4: dynamic outreach email dispatches via Brevo SMTP API."""
    try:
        payload = request.json or {}
        contacts = payload.get("contacts", [])
        
        if not contacts:
            return jsonify({"success": False, "error": "No contacts selected for email outreach."}), 400
            
        logger.info(f"Web API: Dispatching dynamic email outreach campaign to {len(contacts)} contacts.")
        results = BrevoService.send_outreach_campaign(contacts)
        
        successful_sends = sum(1 for item in results if "sent" in item["status"])
        failed_sends = sum(1 for item in results if item["status"] == "failed")
        
        return jsonify({
            "success": True,
            "results": results,
            "sent_count": successful_sends,
            "failed_count": failed_sends
        })
        
    except Exception as e:
        logger.error(f"Web API Stage 4 campaign failure: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/history", methods=["GET"])
def get_history():
    """Reads CSV database logs and returns formatted historic logs data lists."""
    try:
        companies_list = []
        contacts_list = []
        emails_list = []
        
        if Config.COMPANIES_CSV.exists():
            companies_list = pd.read_csv(Config.COMPANIES_CSV).to_dict(orient="records")
        if Config.CONTACTS_CSV.exists():
            contacts_list = pd.read_csv(Config.CONTACTS_CSV).to_dict(orient="records")
        if Config.EMAILS_CSV.exists():
            emails_list = pd.read_csv(Config.EMAILS_CSV).to_dict(orient="records")
            
        return jsonify({
            "success": True,
            "companies": companies_list,
            "contacts": contacts_list,
            "emails": emails_list
        })
        
    except Exception as e:
        logger.error(f"Web API history database read error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    logger.info("Initializing Flask web outreach dashboard on port 5001.")
    app.run(host="127.0.0.1", port=5001, debug=True)

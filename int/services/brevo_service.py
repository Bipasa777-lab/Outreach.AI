import requests
from config import Config
from utils.logger import logger
from utils.helpers import retry_api

class BrevoService:
    """Service layer representing Stage 4 of the pipeline: email personalization and dispatch via Brevo."""
    
    @staticmethod
    def personalize_email(contact: dict) -> tuple[str, str]:
        """Injects prospect credentials (name, job, company) into configured outreach templates."""
        full_name = contact.get("full_name", "there").strip()
        first_name = full_name.split()[0] if len(full_name.split()) > 0 else "there"
        
        # Format human readable company name from domain if company_name is missing
        domain = contact.get("company_domain", "your company")
        company_name = domain.split('.')[0].capitalize()
        
        job_title = contact.get("job_title", "Decision Maker").strip()
        
        # Replace template placeholders
        subject = Config.EMAIL_SUBJECT_TEMPLATE.format(company=company_name)
        body = Config.EMAIL_BODY_TEMPLATE.format(
            first_name=first_name,
            company=company_name,
            job_title=job_title,
            sender_name=Config.SENDER_NAME
        )
        return subject, body

    @staticmethod
    @retry_api()
    def _call_brevo_api(email: str, name: str, subject: str, body: str) -> requests.Response:
        """Invokes POST request to Brevo SMTP email dispatch endpoint."""
        headers = {
            "api-key": Config.BREVO_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Build HTML copy of text layout
        html_body = f"<html><body>{body.replace(chr(10), '<br>')}</body></html>"
        
        payload = {
            "sender": {
                "name": Config.SENDER_NAME,
                "email": Config.SENDER_EMAIL
            },
            "to": [
                {
                    "email": email,
                    "name": name
                }
            ],
            "subject": subject,
            "textContent": body,
            "htmlContent": html_body
        }
        return requests.post(
            Config.BREVO_API_URL,
            headers=headers,
            json=payload,
            timeout=Config.HTTP_TIMEOUT
        )

    @classmethod
    def send_outreach_campaign(cls, contacts: list[dict]) -> list[dict]:
        """
        Executes Stage 4: Generates custom outreach copy and sends transactional email to 
        the target list. Returns dictionary tracking dispatch status.
        """
        logger.info(f"Stage 4: Commencing outreach campaign for {len(contacts)} prospects.")
        results = []
        
        for contact in contacts:
            email = contact.get("email")
            name = contact.get("full_name", "Prospect")
            
            if not email:
                logger.warning(f"Skipping contact '{name}': no email address available.")
                continue
                
            subject, body = cls.personalize_email(contact)
            
            # Check for mock fallback execution
            if not Config.BREVO_API_KEY or Config.BREVO_API_KEY == "mock_brevo_key":
                logger.info(f"Brevo API (MOCK SEND) -> Target: {email}")
                logger.info(f"Subject: {subject}")
                logger.info("Body Content:\n" + body)
                logger.info("=" * 60)
                
                results.append({
                    "email": email,
                    "name": name,
                    "subject": subject,
                    "status": "sent (mock)",
                    "error": None
                })
            else:
                try:
                    response = cls._call_brevo_api(email, name, subject, body)
                    if response.status_code in (200, 201, 202):
                        logger.info(f"Brevo dispatch successful to: {email}")
                        results.append({
                            "email": email,
                            "name": name,
                            "subject": subject,
                            "status": "sent",
                            "error": None
                        })
                    else:
                        error_log = f"HTTP {response.status_code}: {response.text}"
                        logger.error(f"Brevo dispatch failure to {email}: {error_log}")
                        results.append({
                            "email": email,
                            "name": name,
                            "subject": subject,
                            "status": "failed",
                            "error": error_log
                        })
                except Exception as e:
                    logger.error(f"Brevo request failed for {email}: {e}")
                    results.append({
                        "email": email,
                        "name": name,
                        "subject": subject,
                        "status": "failed",
                        "error": str(e)
                    })
                    
        logger.info(f"Stage 4 Complete: Dispatched {len([r for r in results if 'sent' in r['status']])}/{len(results)} emails.")
        return results

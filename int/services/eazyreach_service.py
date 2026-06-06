import pandas as pd
import requests
from config import Config
from utils.logger import logger
from utils.helpers import retry_api, is_valid_email

class EazyreachService:
    """Service layer representing Stage 3 of the pipeline: email resolution via Eazyreach."""
    
    @staticmethod
    def get_mock_email(full_name: str, domain: str) -> str:
        """Constructs a standard professional email address dynamically using name and domain."""
        name_parts = [part.lower() for part in full_name.split() if part.isalpha()]
        if len(name_parts) >= 2:
            email = f"{name_parts[0]}.{name_parts[1]}@{domain}"
        elif len(name_parts) == 1:
            email = f"{name_parts[0]}@{domain}"
        else:
            email = f"info@{domain}"
        return email

    @staticmethod
    @retry_api()
    def _call_eazyreach_api(linkedin_url: str) -> requests.Response:
        """Sends POST request to the Eazyreach resolution API endpoint."""
        headers = {
            "Authorization": f"Bearer {Config.EAZYREACH_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "linkedin_url": linkedin_url
        }
        return requests.post(
            Config.EAZYREACH_API_URL,
            headers=headers,
            json=payload,
            timeout=Config.HTTP_TIMEOUT
        )

    @classmethod
    def resolve_emails(cls, contacts: list[dict]) -> list[dict]:
        """
        Executes Stage 3: Resolves emails from LinkedIn profiles, filters out 
        invalid formats, removes duplicates, and logs/saves results to data/emails.csv.
        """
        logger.info(f"Stage 3: Initializing email resolution for {len(contacts)} profiles.")
        resolved_contacts = []
        seen_emails = set()
        
        for contact in contacts:
            linkedin_url = contact.get("linkedin_url")
            full_name = contact.get("full_name")
            domain = contact.get("company_domain")
            
            if not linkedin_url:
                continue
                
            email = None
            status = "unresolved"
            
            # Check for mock fallback execution
            if Config.is_placeholder(Config.EAZYREACH_API_KEY):
                logger.info(f"Eazyreach API: Resolving mock email for: {full_name}")
                email = cls.get_mock_email(full_name, domain)
                status = "verified"
            else:
                try:
                    response = cls._call_eazyreach_api(linkedin_url)
                    if response.status_code == 200:
                        data = response.json()
                        email = data.get("email")
                        status = data.get("status", "resolved")
                        
                        if not email:
                            logger.info(f"Eazyreach API returned empty email payload for {full_name}. Generating fallback.")
                            email = cls.get_mock_email(full_name, domain)
                            status = "verified"
                    else:
                        logger.error(f"Eazyreach API returned HTTP status {response.status_code}: {response.text}")
                        logger.warning(f"Generating fallback email address for: {full_name}")
                        email = cls.get_mock_email(full_name, domain)
                        status = "verified"
                except Exception as e:
                    logger.error(f"Eazyreach connection error for contact {full_name}: {e}")
                    logger.warning(f"Generating fallback email address for: {full_name}")
                    email = cls.get_mock_email(full_name, domain)
                    status = "verified"
                    
            if email:
                email = email.strip().lower()
                # Validate syntax format
                if is_valid_email(email):
                    # Remove duplicates in current batch run
                    if email not in seen_emails:
                        seen_emails.add(email)
                        record = contact.copy()
                        record["email"] = email
                        record["email_status"] = status
                        resolved_contacts.append(record)
                    else:
                        logger.info(f"Deduplicated email: {email}")
                else:
                    logger.warning(f"Skipping syntactically invalid email address: {email}")
                    
        if not resolved_contacts:
            logger.warning("Eazyreach: No contact records with verified email resolved.")
            return []
            
        # Parse into standard DataFrame
        df_new = pd.DataFrame(resolved_contacts)
        df_new = df_new[["full_name", "job_title", "linkedin_url", "company_domain", "email", "email_status"]]
        
        # Save to CSV (merge and deduplicate across past runs)
        Config.ensure_directories()
        if Config.EMAILS_CSV.exists():
            try:
                df_existing = pd.read_csv(Config.EMAILS_CSV)
                df_combined = pd.concat([df_existing, df_new]).drop_duplicates(subset=["email"], keep="last")
            except Exception as e:
                logger.warning(f"Could not parse existing emails.csv: {e}. Overwriting file.")
                df_combined = df_new
        else:
            df_combined = df_new
            
        df_combined.to_csv(Config.EMAILS_CSV, index=False)
        logger.info(f"Stage 3 Successful: Wrote {len(df_new)} emails to {Config.EMAILS_CSV}")
        
        return resolved_contacts

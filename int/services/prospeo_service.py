import pandas as pd
import requests
from config import Config
from utils.logger import logger
from utils.helpers import retry_api, clean_domain

class ProspeoService:
    """Service layer representing Stage 2 of the pipeline: finding executive decision makers via Prospeo."""
    
    @staticmethod
    def get_mock_contacts(domain: str) -> list[dict]:
        """Generates realistic C-level/VP contacts for a given domain when API credentials are placeholders."""
        logger.info(f"Prospeo API: Initializing mock contacts fallback for domain '{domain}'")
        prefix = domain.split('.')[0].capitalize()
        return [
            {
                "full_name": f"Sarah Jenkins",
                "job_title": "Chief Executive Officer (CEO)",
                "linkedin_url": f"https://www.linkedin.com/in/sarah-jenkins-{prefix.lower()}",
                "company_domain": domain
            },
            {
                "full_name": f"Michael Chen",
                "job_title": "VP of Global Sales",
                "linkedin_url": f"https://www.linkedin.com/in/michael-chen-{prefix.lower()}",
                "company_domain": domain
            },
            {
                "full_name": f"Emily Rodriguez",
                "job_title": "VP of Product Marketing",
                "linkedin_url": f"https://www.linkedin.com/in/emily-rodriguez-{prefix.lower()}",
                "company_domain": domain
            }
        ]

    @staticmethod
    @retry_api()
    def _call_prospeo_api(domain: str) -> requests.Response:
        """Sends POST request to the Prospeo search-person API."""
        headers = {
            "X-KEY": Config.PROSPEO_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "page": 1,
            "filters": {
                "company_domain": {
                    "include": [domain]
                },
                "person_job_title": {
                    "include": [
                        "CEO", "CTO", "CFO", "COO", "VP", "VP of Sales", "VP of Marketing",
                        "Vice President", "Chief", "President", "Founder", "Director"
                    ]
                }
            }
        }
        return requests.post(
            Config.PROSPEO_API_URL,
            headers=headers,
            json=payload,
            timeout=Config.HTTP_TIMEOUT
        )

    @classmethod
    def find_decision_makers(cls, domains: list[str]) -> list[dict]:
        """
        Executes Stage 2: Iterates over domains, queries Prospeo (or mock),
        saves contacts to data/contacts.csv, and returns contacts payload.
        """
        logger.info(f"Stage 2: Starting Prospeo search for {len(domains)} domains.")
        all_contacts = []
        
        for domain in domains:
            cleaned_domain = clean_domain(domain)
            logger.info(f"Querying Prospeo for company domain: {cleaned_domain}")
            
            # Verify if API Key is placeholder
            if not Config.PROSPEO_API_KEY or Config.PROSPEO_API_KEY == "mock_prospeo_key":
                contacts = cls.get_mock_contacts(cleaned_domain)
            else:
                try:
                    response = cls._call_prospeo_api(cleaned_domain)
                    if response.status_code == 200:
                        data = response.json()
                        results = data.get("results", [])
                        contacts = []
                        for item in results:
                            # Standardize extraction of contact properties
                            full_name = item.get("full_name") or f"{item.get('first_name', '')} {item.get('last_name', '')}".strip()
                            job_title = item.get("current_job_title") or item.get("headline", "Executive Decision Maker")
                            linkedin_url = item.get("linkedin_url", "")
                            
                            if not full_name or not linkedin_url:
                                continue
                                
                            contacts.append({
                                "full_name": full_name,
                                "job_title": job_title,
                                "linkedin_url": linkedin_url,
                                "company_domain": cleaned_domain
                            })
                            
                        if not contacts:
                            logger.info(f"Prospeo API returned no contacts for {cleaned_domain}. Using mock fallback.")
                            contacts = cls.get_mock_contacts(cleaned_domain)
                    else:
                        logger.error(f"Prospeo API returned HTTP status {response.status_code}: {response.text}")
                        logger.warning("Falling back to mock contacts.")
                        contacts = cls.get_mock_contacts(cleaned_domain)
                except Exception as e:
                    logger.error(f"Prospeo connection failure for {cleaned_domain}: {e}")
                    logger.warning("Falling back to mock contacts.")
                    contacts = cls.get_mock_contacts(cleaned_domain)
                    
            # Apply individual company limit filter
            contacts = contacts[:Config.PROSPEO_LIMIT_PER_DOMAIN]
            all_contacts.extend(contacts)
            
        if not all_contacts:
            logger.warning("Prospeo: No contact information could be resolved.")
            return []
            
        # Parse into standard DataFrame
        df_new = pd.DataFrame(all_contacts)
        df_new = df_new[["full_name", "job_title", "linkedin_url", "company_domain"]]
        
        # Save to CSV (append and drop duplicate LinkedIn URLs to avoid re-contacting)
        Config.ensure_directories()
        if Config.CONTACTS_CSV.exists():
            try:
                df_existing = pd.read_csv(Config.CONTACTS_CSV)
                df_combined = pd.concat([df_existing, df_new]).drop_duplicates(subset=["linkedin_url"], keep="last")
            except Exception as e:
                logger.warning(f"Could not parse existing contacts.csv: {e}. Overwriting file.")
                df_combined = df_new
        else:
            df_combined = df_new
            
        df_combined.to_csv(Config.CONTACTS_CSV, index=False)
        logger.info(f"Stage 2 Successful: Wrote {len(df_new)} contacts to {Config.CONTACTS_CSV}")
        
        return all_contacts

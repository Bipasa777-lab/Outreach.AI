import pandas as pd
import requests
from config import Config
from utils.logger import logger
from utils.helpers import retry_api, clean_domain

class OceanService:
    """Service layer representing Stage 1 of the pipeline: lookalike discovery via Ocean.io."""
    
    @staticmethod
    def get_mock_lookalikes(seed_domain: str) -> list[dict]:
        """Generates realistic lookalike business domains when API credentials are placeholders."""
        logger.info(f"Ocean.io API: Initializing mock fallback for domain '{seed_domain}'")
        
        domain_parts = seed_domain.split('.')
        base = domain_parts[0] if len(domain_parts) > 1 else seed_domain
        
        if base in ("hubspot", "salesforce", "zoho", "pipedrive"):
            return [
                {"name": "Salesforce Inc.", "domain": "salesforce.com"},
                {"name": "Zoho Corporation", "domain": "zoho.com"},
                {"name": "Pipedrive CRM", "domain": "pipedrive.com"},
                {"name": "ActiveCampaign LLC", "domain": "activecampaign.com"},
                {"name": "Keap CRM", "domain": "keap.com"},
            ]
        else:
            return [
                {"name": f"{base.capitalize()} Solutions", "domain": f"{base}solutions.com"},
                {"name": f"{base.capitalize()} Technologies", "domain": f"{base}tech.io"},
                {"name": f"{base.capitalize()} Global Group", "domain": f"{base}global.net"},
                {"name": f"Competitor of {base.capitalize()}", "domain": f"{base}-alternative.com"},
                {"name": f"{base.capitalize()} Systems", "domain": f"{base}sys.com"}
            ]

    @staticmethod
    @retry_api()
    def _call_ocean_api(seed_domain: str) -> requests.Response:
        """Sends POST query to the Ocean.io lookalike API."""
        headers = {
            "X-Api-Token": Config.OCEAN_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "size": Config.OCEAN_LIMIT,
            "fields": ["domain", "name"],
            "companiesFilters": {
                "seedDomains": [seed_domain]
            }
        }
        return requests.post(
            Config.OCEAN_API_URL,
            headers=headers,
            json=payload,
            timeout=Config.HTTP_TIMEOUT
        )

    @classmethod
    def get_lookalike_companies(cls, seed_domain: str) -> list[str]:
        """
        Executes Stage 1: Accepts seed domain, queries Ocean.io (or mock),
        saves outcomes to data/companies.csv and returns lookalike domains list.
        """
        cleaned_seed = clean_domain(seed_domain)
        logger.info(f"Stage 1: Beginning Ocean.io search for seed domain: {cleaned_seed}")
        
        # Verify if API Key is placeholder
        if not Config.OCEAN_API_KEY or Config.OCEAN_API_KEY == "mock_ocean_key":
            companies = cls.get_mock_lookalikes(cleaned_seed)
        else:
            try:
                response = cls._call_ocean_api(cleaned_seed)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    companies = []
                    for item in results:
                        name = item.get("name", "Unknown Company")
                        domain = item.get("domain", "")
                        if domain:
                            companies.append({"name": name, "domain": clean_domain(domain)})
                else:
                    logger.error(f"Ocean.io API returned HTTP status {response.status_code}: {response.text}")
                    logger.warning("Failing back to mock data lookup.")
                    companies = cls.get_mock_lookalikes(cleaned_seed)
            except Exception as e:
                logger.error(f"Ocean.io connection failure: {e}")
                logger.warning("Failing back to mock lookalike companies.")
                companies = cls.get_mock_lookalikes(cleaned_seed)
                
        if not companies:
            logger.warning("Ocean.io: No lookalikes resolved.")
            return []
            
        # Parse into standard DataFrame
        df_new = pd.DataFrame(companies)
        df_new["seed_domain"] = cleaned_seed
        df_new.rename(columns={"name": "company_name", "domain": "company_domain"}, inplace=True)
        # Order columns logically
        df_new = df_new[["seed_domain", "company_name", "company_domain"]]
        
        # Save to CSV (append and drop duplicate domains to prevent bloat)
        Config.ensure_directories()
        if Config.COMPANIES_CSV.exists():
            try:
                df_existing = pd.read_csv(Config.COMPANIES_CSV)
                df_combined = pd.concat([df_existing, df_new]).drop_duplicates(subset=["company_domain"], keep="last")
            except Exception as e:
                logger.warning(f"Could not parse existing companies.csv: {e}. Overwriting file.")
                df_combined = df_new
        else:
            df_combined = df_new
            
        df_combined.to_csv(Config.COMPANIES_CSV, index=False)
        logger.info(f"Stage 1 Successful: Wrote {len(df_new)} lookalikes to {Config.COMPANIES_CSV}")
        
        return df_new["company_domain"].tolist()

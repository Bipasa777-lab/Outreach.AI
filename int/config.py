import os
from pathlib import Path
from dotenv import load_dotenv

# Resolve paths
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from .env
load_dotenv(dotenv_path=BASE_DIR / ".env")

class Config:
    """Application configuration and credentials loader."""
    
    # API Keys
    OCEAN_API_KEY: str = os.getenv("OCEAN_API_KEY", "").strip()
    PROSPEO_API_KEY: str = os.getenv("PROSPEO_API_KEY", "").strip()
    EAZYREACH_API_KEY: str = os.getenv("EAZYREACH_API_KEY", "").strip()
    BREVO_API_KEY: str = os.getenv("BREVO_API_KEY", "").strip()

    # Sender Details
    SENDER_NAME: str = os.getenv("SENDER_NAME", "Outreach Agent").strip()
    SENDER_EMAIL: str = os.getenv("SENDER_EMAIL", "sender@example.com").strip()

    # API Base Endpoints
    OCEAN_API_URL: str = "https://api.ocean.io/v2/lookalike/companies/search"
    PROSPEO_API_URL: str = "https://api.prospeo.io/search-person"
    EAZYREACH_API_URL: str = "https://api.eazyreach.app/v1/resolve"
    BREVO_API_URL: str = "https://api.brevo.com/v3/smtp/email"

    # Default API Parameters & Limits
    OCEAN_LIMIT: int = 10
    PROSPEO_LIMIT_PER_DOMAIN: int = 5
    HTTP_TIMEOUT: int = 30  # seconds

    # File Storage Paths
    DATA_DIR: Path = BASE_DIR / "data"
    LOGS_DIR: Path = BASE_DIR / "logs"

    COMPANIES_CSV: Path = DATA_DIR / "companies.csv"
    CONTACTS_CSV: Path = DATA_DIR / "contacts.csv"
    EMAILS_CSV: Path = DATA_DIR / "emails.csv"
    APP_LOG: Path = LOGS_DIR / "app.log"

    # Email Outreach Template
    EMAIL_SUBJECT_TEMPLATE: str = "Quick idea for {company}"
    EMAIL_BODY_TEMPLATE: str = (
        "Hi {first_name},\n\n"
        "I came across {company} and noticed your role as {job_title}.\n\n"
        "We help companies improve outreach automation and lead generation through AI-powered workflows.\n\n"
        "Would you be open to a quick discussion?\n\n"
        "Regards,\n"
        "{sender_name}"
    )

    @classmethod
    def ensure_directories(cls) -> None:
        """Ensures directories exist for data and log exports."""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_missing_credentials(cls) -> list[str]:
        """Identifies missing or default mock environment variables."""
        missing = []
        placeholders = {"mock_ocean_key", "mock_prospeo_key", "mock_eazyreach_key", "mock_brevo_key", ""}
        
        if cls.OCEAN_API_KEY in placeholders:
            missing.append("OCEAN_API_KEY")
        if cls.PROSPEO_API_KEY in placeholders:
            missing.append("PROSPEO_API_KEY")
        if cls.EAZYREACH_API_KEY in placeholders:
            missing.append("EAZYREACH_API_KEY")
        if cls.BREVO_API_KEY in placeholders:
            missing.append("BREVO_API_KEY")
            
        return missing

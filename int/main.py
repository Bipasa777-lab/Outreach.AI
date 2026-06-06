import sys
from config import Config
from utils.logger import logger
from utils.helpers import is_valid_domain, clean_domain
from services.ocean_service import OceanService
from services.prospeo_service import ProspeoService
from services.eazyreach_service import EazyreachService
from services.brevo_service import BrevoService

def run_pipeline() -> None:
    """Orchestrates the four stages of the Automated Outreach Pipeline."""
    logger.info("Initializing Automated Outreach Pipeline runner.")
    
    # 1. Initialize data folders
    Config.ensure_directories()
    
    # 2. Check and report placeholder keys
    missing_credentials = Config.get_missing_credentials()
    if missing_credentials:
        logger.warning(
            f"The following required configuration keys are unset: {', '.join(missing_credentials)}. "
            "Pipeline will execute with mock data fallbacks where key configurations are missing."
        )
        
    print("\n==================================================")
    print("         Automated Outreach Pipeline CLI")
    print("==================================================\n")
    
    # 3. Prompt user for seed company domain
    try:
        raw_input_domain = input("Enter Company Domain: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\n\nPipeline canceled by user request. Exiting.")
        sys.exit(0)
        
    if not raw_input_domain:
        logger.error("Domain input cannot be blank.")
        sys.exit(1)
        
    if not is_valid_domain(raw_input_domain):
        logger.error(f"Invalid company domain format: '{raw_input_domain}'. Please enter a format like 'hubspot.com'.")
        sys.exit(1)
        
    cleaned_seed_domain = clean_domain(raw_input_domain)
    logger.info(f"Target Seed Domain: {cleaned_seed_domain}")
    
    # Stage 1: Ocean.io lookup for lookalike companies
    try:
        lookalike_domains = OceanService.get_lookalike_companies(cleaned_seed_domain)
    except Exception as e:
        logger.critical(f"Stage 1 (Ocean.io lookup) failed critically: {e}")
        sys.exit(1)
        
    if not lookalike_domains:
        logger.error("Abort: No lookalike companies were returned in Stage 1.")
        sys.exit(1)
        
    # Stage 2: Prospeo lookup for C-level/VP contacts
    try:
        contacts = ProspeoService.find_decision_makers(lookalike_domains)
    except Exception as e:
        logger.critical(f"Stage 2 (Prospeo lead generation) failed critically: {e}")
        sys.exit(1)
        
    if not contacts:
        logger.error("Abort: No executive contacts were found in Stage 2.")
        sys.exit(1)
        
    # Stage 3: Eazyreach lookup for verified emails
    try:
        resolved_leads = EazyreachService.resolve_emails(contacts)
    except Exception as e:
        logger.critical(f"Stage 3 (Eazyreach email resolution) failed critically: {e}")
        sys.exit(1)
        
    if not resolved_leads:
        logger.error("Abort: No verified emails were resolved in Stage 3.")
        sys.exit(1)
        
    # Safety Checkpoint Summary
    total_companies = len(lookalike_domains)
    total_contacts = len(contacts)
    total_emails = len(resolved_leads)
    
    print("\n--------------------------------------------------")
    print(f"Total Companies Found: {total_companies}")
    print(f"Total Contacts Found:  {total_contacts}")
    print(f"Total Emails Resolved:  {total_emails}")
    print("--------------------------------------------------\n")
    
    try:
        user_choice = input("Do you want to send emails? (y/n): ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print("\n\nCampaign aborted at safety checkpoint. Exiting.")
        sys.exit(0)
        
    if user_choice not in ("y", "yes"):
        logger.info("Safety Checkpoint: User rejected email campaign dispatch.")
        print("\nOutreach skipped. Outputs are exported to CSV files. Goodbye!")
        sys.exit(0)
        
    # Stage 4: Brevo dynamic email outreach dispatch
    try:
        results = BrevoService.send_outreach_campaign(resolved_leads)
    except Exception as e:
        logger.critical(f"Stage 4 (Brevo email outreach) failed critically: {e}")
        sys.exit(1)
        
    # Compile execution report statistics
    successful_sends = sum(1 for item in results if "sent" in item["status"])
    failed_sends = sum(1 for item in results if item["status"] == "failed")
    
    print("\n--------------------------------------------------")
    print("Campaign complete!")
    print(f"Total Dispatched: {successful_sends}")
    print(f"Total Failed:     {failed_sends}")
    print("--------------------------------------------------\n")
    logger.info(f"Outreach Finished. Total Success: {successful_sends}, Total Failed: {failed_sends}")

if __name__ == "__main__":
    run_pipeline()

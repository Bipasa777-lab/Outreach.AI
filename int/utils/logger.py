import logging
import sys
from config import Config

def setup_logger(name: str = "outreach_pipeline") -> logging.Logger:
    """Initializes a double-output logger (writes to stdout and to config-defined log file)."""
    Config.ensure_directories()
    
    logger = logging.getLogger(name)
    # Prevent duplicate handlers if multiple modules call setup_logger
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        # File Logger Handler
        try:
            file_handler = logging.FileHandler(Config.APP_LOG, encoding="utf-8")
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.INFO)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"Warning: Unable to bind file log handler: {e}", file=sys.stderr)
            
        # Console Output Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)
        
    return logger

# Singleton application logger instance
logger = setup_logger()

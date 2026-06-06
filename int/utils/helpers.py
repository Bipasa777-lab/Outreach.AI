import re
import time
import functools
from typing import Callable, Any
import requests
from utils.logger import logger

# Regex patterns for input validation
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
DOMAIN_REGEX = re.compile(r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}$")

def is_valid_email(email: str) -> bool:
    """Verifies if the email string aligns with standard structure."""
    if not email:
        return False
    return bool(EMAIL_REGEX.match(email.strip()))

def clean_domain(domain: str) -> str:
    """Cleans up url protocol prefixes, www prefixes, queries and paths to return the raw domain."""
    if not domain:
        return ""
    cleaned = domain.strip().lower()
    cleaned = re.sub(r"^https?://", "", cleaned)
    cleaned = re.sub(r"^www\.", "", cleaned)
    cleaned = cleaned.split("/")[0]
    cleaned = cleaned.split("?")[0]
    return cleaned

def is_valid_domain(domain: str) -> bool:
    """Checks if the cleaned domain is valid syntactically."""
    cleaned = clean_domain(domain)
    return bool(DOMAIN_REGEX.match(cleaned))

def retry_api(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    status_codes_to_retry: list[int] = [429, 500, 502, 503, 504]
) -> Callable:
    """
    Decorator to wrap HTTP-requests for retry capability.
    Handles rate-limiting (429) using Retry-After headers if available.
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = initial_delay
            last_exception = None
            
            for attempt in range(1, max_retries + 1):
                try:
                    response = func(*args, **kwargs)
                    
                    if isinstance(response, requests.Response):
                        # Treat HTTP 429 specially
                        if response.status_code == 429:
                            retry_after = response.headers.get("Retry-After")
                            wait_time = delay
                            if retry_after:
                                try:
                                    wait_time = float(retry_after)
                                except ValueError:
                                    pass
                            logger.warning(
                                f"Rate limit (429) hit in {func.__name__}. "
                                f"Attempt {attempt}/{max_retries}. Waiting {wait_time}s..."
                            )
                            time.sleep(wait_time)
                            delay *= backoff_factor
                            continue
                            
                        # Other transient status codes
                        elif response.status_code in status_codes_to_retry:
                            logger.warning(
                                f"Transient status {response.status_code} in {func.__name__}. "
                                f"Attempt {attempt}/{max_retries}. Retrying in {delay}s..."
                            )
                            time.sleep(delay)
                            delay *= backoff_factor
                            continue
                            
                    return response
                    
                except requests.RequestException as e:
                    last_exception = e
                    if attempt == max_retries:
                        logger.error(f"API call {func.__name__} exhausted {max_retries} attempts: {e}")
                        raise
                    logger.warning(
                        f"RequestException in {func.__name__} ({e}). "
                        f"Attempt {attempt}/{max_retries}. Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                    delay *= backoff_factor
                    
            if last_exception:
                raise last_exception
            raise requests.RequestException(f"API operation {func.__name__} failed after {max_retries} attempts.")
        return wrapper
    return decorator

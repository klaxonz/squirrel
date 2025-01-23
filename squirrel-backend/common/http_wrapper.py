import json
import logging
import time
from typing import Optional, Union, Any
from urllib.parse import urlparse, parse_qs
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from json.decoder import JSONDecodeError
from requests.exceptions import RequestException
from urllib3.exceptions import HTTPError
from core.database import get_session
from models.request_log import ExternalRequestLog
from utils.rate_limiter import rate_limiter

logger = logging.getLogger()


def truncate_text(text: str, max_length: int = 65535) -> str:
    """Safely truncate text to maximum length"""
    if text and len(text) > max_length:
        return text[:max_length]
    return text


def safe_json_dumps(obj: Any, max_length: int = 65535) -> Optional[str]:
    """Safely convert object to JSON string with length limit"""
    if obj is None:
        return None
    try:
        return truncate_text(json.dumps(obj), max_length)
    except Exception as e:
        logger.error(f"JSON serialization error: {str(e)}")
        return None


def log_request(
        url: str,
        method: str,
        params: Optional[Union[dict, str]] = None,
        body: Optional[Union[dict, str]] = None,
        response: Optional[requests.Response] = None,
        duration: float = 0,
        error: Optional[str] = None
):
    """Log external request"""
    try:
        domain = urlparse(url).netloc.replace('www.', '')
        response_text = None
        status_code = None
        size = 0

        if response:
            try:
                if response.headers.get('content-type', '').startswith('application/json'):
                    response_text = safe_json_dumps(response.json())
                else:
                    response_text = truncate_text(response.text)
                status_code = response.status_code
                size = len(response.content)
            except Exception as e:
                logger.error(f"Failed to process response: {str(e)}")

        log = ExternalRequestLog(
            url=truncate_text(url, 1024),
            domain=truncate_text(domain, 255),
            method=truncate_text(method, 10),
            params=safe_json_dumps(params),
            body=safe_json_dumps(body),
            response=response_text,
            size=size,
            status_code=status_code or 0,
            duration=duration,
            error=truncate_text(error, 65535) if error else None
        )

        with get_session() as db_session:
            db_session.add(log)
            db_session.commit()
    except Exception as e:
        logger.error(f"Failed to log request: {str(e)}")


class RateLimitAdapter(HTTPAdapter):
    """HTTP adapter that implements rate limiting"""

    def send(self, request, **kwargs):
        """Send request with rate limiting"""
        start_time = time.time()
        error = None
        response = None
        
        try:
            domain = urlparse(request.url).netloc.replace('www.', '')
            rate_limiter.wait(domain)
            response = super().send(request, **kwargs)
            return response
        except (RequestException, HTTPError) as e:
            error = str(e)
            raise
        finally:
            try:
                duration = (time.time() - start_time) * 1000
                
                params = getattr(request, 'params', None)
                if params is None and hasattr(request, 'prepare'):
                    parsed = urlparse(request.url)
                    params = parse_qs(parsed.query)
                
                body = None
                if hasattr(request, 'body') and request.body:
                    try:
                        if isinstance(request.body, bytes):
                            body = request.body.decode('utf-8')
                        elif isinstance(request.body, str):
                            body = request.body
                        else:
                            body = str(request.body)
                    except UnicodeDecodeError as e:
                        logger.warning(f"Failed to decode request body: {str(e)}")
                        body = str(request.body)
                
                log_request(
                    url=request.url,
                    method=request.method,
                    params=params,
                    body=body,
                    response=response,
                    duration=duration,
                    error=error
                )
            except (IOError, JSONDecodeError) as e:
                logger.error(f"Failed to log request in adapter: {str(e)}")


class Session(requests.Session):
    def __init__(self, retries: int = 3, backoff_factor: float = 0.3):
        super().__init__()

        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=(500, 502, 504),
        )

        adapter = RateLimitAdapter(max_retries=retry)
        self.mount("http://", adapter)
        self.mount("https://", adapter)


session = Session()

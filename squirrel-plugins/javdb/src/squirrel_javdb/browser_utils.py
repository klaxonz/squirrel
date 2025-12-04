"""Browser utilities for bypassing Cloudflare and other protection mechanisms."""

from __future__ import annotations

import logging
import time
from typing import Optional, Any

from botasaurus.browser import Driver, browser as bbrowser

logger = logging.getLogger(__name__)


class CloudflareBypassConfig:
	
	def __init__(
		self,
		max_verification_attempts: int = 5,
		max_wait_time: int = 60,
		check_interval: int = 3,
		initial_wait: int = 2,
		body_wait_timeout: int = 15,
		min_content_length: int = 500,
		debug: bool = False,
	):
		self.max_verification_attempts = max_verification_attempts
		self.max_wait_time = max_wait_time
		self.check_interval = check_interval
		self.initial_wait = initial_wait
		self.body_wait_timeout = body_wait_timeout
		self.min_content_length = min_content_length
		self.debug = debug


def fetch_with_cloudflare_bypass(
	driver: Driver,
	url: str,
	config: Optional[CloudflareBypassConfig] = None,
) -> str:
	"""Fetch HTML with Cloudflare bypass support."""
	if config is None:
		config = CloudflareBypassConfig()
	
	try:
		driver.google_get(url, bypass_cloudflare=True)
		time.sleep(config.initial_wait)
		
		try:
			driver.wait_for_element('body', wait=config.body_wait_timeout)
		except Exception:
			logger.warning(f"Body element not found quickly for {url}")
		
		total_wait = 0
		verification_count = 0
		
		while total_wait < config.max_wait_time and verification_count < config.max_verification_attempts:
			html = driver.page_html
			html_lower = html.lower()
			
			is_cloudflare_challenge = (
				'cloudflare' in html_lower and 
				('checking your browser' in html_lower or 
				 'just a moment' in html_lower or
				 'please wait' in html_lower or
				 'verify you are human' in html_lower)
			)
			
			if not is_cloudflare_challenge:
				if len(html) > config.min_content_length and '<body' in html_lower:
					logger.info(f"Successfully loaded {url} after {total_wait}s")
					break
			
			verification_count += 1
			logger.debug(f"Cloudflare verification attempt {verification_count}/{config.max_verification_attempts} for {url}")
			
			time.sleep(config.check_interval)
			total_wait += config.check_interval
			
			try:
				challenge_elements = driver.select('div.cf-browser-verification', wait=1)
				if challenge_elements:
					logger.debug("Detected Cloudflare browser verification")
					time.sleep(5)
			except Exception:
				pass
		
		html = driver.page_html
		
		if config.debug:
			driver.prompt()
		
		if len(html) < config.min_content_length:
			raise Exception(f"Page content too short ({len(html)} bytes)")
		
		if 'cloudflare' in html.lower() and 'checking your browser' in html.lower():
			raise Exception("Failed to bypass Cloudflare after multiple attempts")
		
		return html
		
	except Exception as e:
		logger.error(f"Error fetching {url}: {e}")
		raise


def create_bypass_config(**kwargs: Any) -> CloudflareBypassConfig:
	"""Create CloudflareBypassConfig with custom parameters."""
	return CloudflareBypassConfig(**kwargs)


@bbrowser(
	output=None,
	raise_exception=True,
	close_on_crash=True,
	create_error_logs=False,
	max_retry=3,
	reuse_driver=False,
	block_images_and_css=True,
	headless=True,
	user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
def fetch_page_html(driver: Driver, url: str, debug: bool = False) -> str:
	"""Fetch page HTML with Cloudflare bypass using default config."""
	config = CloudflareBypassConfig(
		max_verification_attempts=5,
		max_wait_time=60,
		min_content_length=1000,
		debug=debug,
	)
	return fetch_with_cloudflare_bypass(driver, url, config)

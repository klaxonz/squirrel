from __future__ import annotations

import re

from crawl import IdExtractor, register_id_extractor


@register_id_extractor
class YoutubeIdExtractor(IdExtractor):
	domain = 'youtube.com'

	def extract_id(self) -> str:
		pattern = r"(?:v=|/)([0-9A-Za-z_-]{11})"
		match = re.search(pattern, self.url)
		if match:
			return match.group(1)
		else:
			raise ValueError("Invalid url")


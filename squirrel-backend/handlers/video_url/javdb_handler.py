import re
from urllib.parse import quote
import cloudscraper
from bs4 import BeautifulSoup
from dto.video_dto import VideoUrlDto
from handlers.video_url.base import VideoUrlHandler, VideoUrlExtractionError
from models.video import Video


class JavdbHandler(VideoUrlHandler):
    """Handler for Javdb video URLs"""
    
    def supports_domain(self, domain: str) -> bool:
        return domain == 'javdb.com'
    
    def get_video_url(self, video: Video) -> VideoUrlDto:
        try:
            proxy_prefix_path = f"/api/video/proxy?domain=javdb.com"
            
            no = video.title.split(' ')[0]
            url = self._get_jav_video_url(no)
            
            if url:
                return VideoUrlDto(
                    video_url=f"{proxy_prefix_path}&url=" + quote(url),
                    audio_url=None,
                )
            else:
                return VideoUrlDto(video_url=None, audio_url=None)
                
        except Exception as e:
            raise VideoUrlExtractionError(f"Failed to extract Javdb video URL: {str(e)}")
    
    def _get_jav_video_url(self, no: str) -> str:
        """Extract JAV video URL from missav.ws"""
        try:
            url = f'https://missav.ws/search/{no}'
            scraper = cloudscraper.create_scraper()
            response = scraper.get(url)
            response.raise_for_status()
            
            bs4 = BeautifulSoup(response.text, 'html.parser')
            items = bs4.select('div.thumbnail')
            
            if len(items) > 0:
                target = items[0]
                target_url = target.select_one('a')['href']
                
                if not target_url.startswith('https://'):
                    return None
                    
                response = scraper.get(target_url)
                response.raise_for_status()
                
                r = self._extract_parts_from_html_content(response.text)
                if not r:
                    return None
                    
                url_path = r.split("m3u8|")[1].split("|playlist|source")[0]
                url_words = url_path.split('|')
                video_index = url_words.index("video")
                protocol = url_words[video_index - 1]
                video_format = url_words[video_index + 1]

                m3u8_url_path = "-".join((url_words[0:5])[::-1])
                base_url_path = ".".join((url_words[5:video_index - 1])[::-1])

                formatted_url = "{0}://{1}/{2}/{3}/{4}.m3u8".format(
                    protocol, base_url_path, m3u8_url_path, video_format, url_words[video_index]
                )
                return formatted_url
                
            return None
            
        except Exception as e:
            raise VideoUrlExtractionError(f"Failed to extract JAV video URL: {str(e)}")
    
    def _extract_parts_from_html_content(self, html_content: str) -> str:
        """Extract video URL parts from HTML content"""
        soup = BeautifulSoup(html_content, 'html.parser')

        for script in soup.find_all('script'):
            if script.string and 'm3u8|' in script.string:
                pattern = r"'([^']*m3u8\|[^']*)'"
                match = re.search(pattern, script.string)
                if match:
                    return match.group(1)
        return None

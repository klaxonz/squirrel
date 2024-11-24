import re

import cloudscraper
from bs4 import BeautifulSoup

# url = "https://javdb.com/actors/9ZAR"
# channel = SubscribeChannelFactory.create_subscribe_channel(url)
# videos = channel.get_channel_videos(None, True)
# print(videos)

# Downloader.get_video_info("https://javdb.com/v/0kKx0")
# up = JavUploader("https://javdb.com/v/0kKx0")
# print(up.get_name())

no = 'AQSH-111'
#
# headers = {
#     'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
#                   'Chrome/124.0.0.0 Safari/537.36',
#     'cookie': 'user_uuid=23c11f34-e430-4ec5-8722-5ba024902373; cf_clearance=IjYAsfufdXg1fVJv.9fexmUGlbMrDUpMm1Ze1wlG2G8-1732369262-1.2.1.1-kXV2Cp2Ul.QkyiYZQeQa0EJaTQRixAPkceE8lD._YG.8WrmQ6OtMVQzuWuE0z9H04DEulZAmCASGg7X2zDEDAENHehLmDUEO9HP_z9QkesTStxEtEq827KEAzL2q4uLN9LdW6Dr7pdIbdP1B9I11KlytOS7YUVzRDiRhziGDR3q1hApZw.zmmv29CZ.p0bcJaL44E5d63w7bOCKcdgme81.DriXS0ulrS8PsAsKPNbpfZUgcpjU1BH2r.OtpTBgJB_Hj7QUWVP.ZYsQa7AzvDgdhEAoBW7MV494FYZsNW9Yr1hAwxQUcw2l48W204rzsf27dShvkYAxRU4Me3MiAGyHBunfCzts7KrXs_fWKrhUsN9z_pTDB1pWVkLKwfYH6; XSRF-TOKEN=eyJpdiI6InhUVFhCaHhvWXE5Ui8zdEs4VmtSZ0E9PSIsInZhbHVlIjoibnM2YXhEbnlFdWJCdExOTnhRT0V2bGZ3Y0MrMllhME02K3dOaVp0Y3hSUjk2ZThHa09KcHlxYUhUL0U5bVlMR3hoS0xJT29qeWx4YTRYUFJkSFY3dS9mdjhpd05YWjY0UmpuUnVFc2w4MEVZZU9xa1dmaVBRTncvbFFqNjlzMWUiLCJtYWMiOiI5MGUwMmZiYWRmNWUzZTYzZWE4Y2Y5MDEwZjZhYWYzMjNiNWFiYTkxYzg0MTc4ZDBhOTI1NTRlMjA5NWUyOTQxIiwidGFnIjoiIn0%3D; missav_session=eyJpdiI6ImZIN2ZwcUp2U2czUWQvdVlmbGQ4aGc9PSIsInZhbHVlIjoiWGVXMFNiSy81VHNPNDM1aVJRaDlhcEpvd0ZmU1BraGllS1R3SXRVczRveVRvWTVnR0tqZ08xZHFhaVRnVTUrOU9NaDNTcnJyQk1ZM2pqeTVpRVhCdWtZMm43Q2kwbnRaMXBsZzVITkJTcHFNb1ZmTzVUU3Fjck1ML0F4VVRiOVciLCJtYWMiOiIyNDM0MzUyMjIyOTgyNDA4ZGZjMDIzNDI3NTlhZGVkOTI2ZjUxOTg5NjBhNmJkYzQzYjcwMzk4YmIyNDEyZGExIiwidGFnIjoiIn0%3D; Ah547LrEuY1MXoxneDQh02OiN6zazofH3FuXzsqq=eyJpdiI6ImxOSFRPVkw1Z2ZwMW4xVFdLeG9OaGc9PSIsInZhbHVlIjoiMW04V2xwWXJXWHRxYllQaUVDbHBzcmRxYitkbzNoelk5Y3JCTmtnUmIySk05N2NvZTQ3Nm1tNGtEei9wUWlZdkRPNnJmajdrTTdTdWUwYjlEeERHZEl1Nm1GUFQyaVZHYkpGazdZajlWcnhIVU4vMTVXTzJkSjVlZW9LNW91N1pvTDExZjNHdUdjUHo2V0JyeHc4VTM1N1VnQkVvVmtNQlZ5eWNWeTBlSHNFWFNlS0JGbXRpbm5CWTVWeGJENjF0ejM5djZRQlN1QUd3KzZWRGEyZGtsek1LNm85cFY4ZEs5MWkvbmxGY0ZQS2piQVA4a0o5RWJWRVlwNExuenRmL0FvQTFUM3BLbDdCVUJVTVRGZzJYYVhzSjYwZlZtaVh4M0h6UVc3WXREa2o2Ly9aSVk4UlBOaVV0RWttKzZwZ0lDY0JtR1doTEFQRXljNlhpZlpsOUZBeTZHZk9icC9wekF0Q0xzV0QyVlZYUXFwRzk5V1lpOVZQN3NPbjZSMjdiazFDRUlyZjk5WkM2bHF4dmY0anNudz09IiwibWFjIjoiYzk0ZDI4YTU0NGFmNjYxMmU5ZmJiNmI5ZjU2YzNiYTFhOGE4ZTgyYTRlOTI0MzlkNDBmNWM3MDVjNjFiZjc1NiIsInRhZyI6IiJ9; search_history=[%22ALDN-348%22%2C%22PRED-699%22%2C%22FC2-1294687%22%2C%22FC2-PPV-3116291%22%2C%22FC2-PPV-311629106%22%2C%22311629106%22]'
# }
url = f'https://missav.com/search/{no}'
# response = session.get(url, headers=headers, timeout=15)
# response.raise_for_status()
# print(response.text)
# bs4 = BeautifulSoup(response.text, 'html.parser')

def extract_parts_from_html_content(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')

    # 查找所有script标签
    for script in soup.find_all('script'):
        if script.string and 'm3u8|' in script.string:
            # 找到包含目标字符串的部分
            pattern = r"'([^']*m3u8\|[^']*)'"
            match = re.search(pattern, script.string)
            if match:
                parts = match.group(1)
                return parts
    return None

scraper = cloudscraper.create_scraper()
response = scraper.get(url)
bs4 = BeautifulSoup(response.text, 'html.parser')
print(response.text)
items = bs4.select('div.thumbnail')
if len(items) > 0:
    target = items[0]
    target_url = target.select_one('a')['href']

    response = scraper.get(target_url)
    r = extract_parts_from_html_content(response.text)
    url_path = r.split("m3u8|")[1].split("|playlist|source")[0]
    url_words = url_path.split('|')
    video_index = url_words.index("video")
    protocol = url_words[video_index-1]
    video_format = url_words[video_index + 1]

    m3u8_url_path = "-".join((url_words[0:5])[::-1])
    base_url_path = ".".join((url_words[5:video_index-1])[::-1])

    formatted_url = "{0}://{1}/{2}/{3}/{4}.m3u8".format(protocol, base_url_path, m3u8_url_path, video_format, url_words[video_index])


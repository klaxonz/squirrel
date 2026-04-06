import os
import re
import tempfile

import requests

from camoufox.__main__ import CamoufoxUpdate
from camoufox.pkgman import CamoufoxFetcher
from camoufox.pkgman import INSTALL_DIR
from camoufox.pkgman import OS_NAME
from camoufox.pkgman import Version


RELEASES_URL = 'https://github.com/daijro/camoufox/releases'


def _github_headers() -> dict[str, str]:
    headers = {
        'User-Agent': 'squirrel-cf-bypass-build/1.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    token = os.environ.get('CAMOUFOX_GITHUB_TOKEN') or os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    if token:
        headers['Authorization'] = f'Bearer {token}'
    return headers


def _build_fallback_fetcher() -> CamoufoxFetcher:
    arch = CamoufoxFetcher.get_platform_arch()
    pattern = re.compile(
        rf'href="(?P<href>/daijro/camoufox/releases/download/[^"]+/camoufox-(?P<version>.+)-(?P<release>.+)-{OS_NAME}\.{arch}\.zip)"'
    )
    response = requests.get(RELEASES_URL, headers=_github_headers(), timeout=20)
    response.raise_for_status()

    seen_urls: set[str] = set()
    for match in pattern.finditer(response.text):
        version = Version(release=match.group('release'), version=match.group('version'))
        if not version.is_supported():
            continue

        url = f'https://github.com{match.group("href")}'
        if url in seen_urls:
            continue
        seen_urls.add(url)

        fetcher = CamoufoxFetcher.__new__(CamoufoxFetcher)
        fetcher.arch = arch
        fetcher._version_obj = version
        fetcher._url = url
        return fetcher

    raise RuntimeError('Unable to find a supported Camoufox release asset from the GitHub releases page.')


def _fallback_fetch() -> None:
    fetcher = _build_fallback_fetcher()
    fetcher.install()


def main() -> None:
    try:
        CamoufoxUpdate().update()
    except requests.HTTPError as exc:
        response = exc.response
        if response is None or response.status_code != 403:
            raise
        print('GitHub API rate limit hit while fetching Camoufox. Falling back to release page scraping.')
        _fallback_fetch()

    if not INSTALL_DIR.exists():
        raise RuntimeError('Camoufox install directory was not created.')


if __name__ == '__main__':
    main()

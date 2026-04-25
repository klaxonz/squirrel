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


def _make_fetcher(version: str, release: str, url: str, arch: str) -> CamoufoxFetcher:
    version_obj = Version(release=release, version=version)
    if not version_obj.is_supported():
        raise RuntimeError(
            f'Camoufox release {version}-{release} is outside the supported range.'
        )

    fetcher = CamoufoxFetcher.__new__(CamoufoxFetcher)
    fetcher.arch = arch
    fetcher._version_obj = version_obj
    fetcher._url = url
    return fetcher


def _build_latest_redirect_fetcher() -> CamoufoxFetcher:
    arch = CamoufoxFetcher.get_platform_arch()
    response = requests.get(
        f'{RELEASES_URL}/latest',
        headers=_github_headers(),
        timeout=20,
        allow_redirects=False,
    )
    response.raise_for_status()

    location = response.headers.get('Location') or response.url
    match = re.search(r'/tag/v?(?P<version>\d+(?:\.\d+)+)-(?P<release>[^/?#]+)', location)
    if not match:
        raise RuntimeError(f'Unable to parse latest Camoufox release tag from {location!r}.')

    version = match.group('version')
    release = match.group('release')
    tag = f'v{version}-{release}'
    url = (
        f'https://github.com/daijro/camoufox/releases/download/{tag}/'
        f'camoufox-{version}-{release}-{OS_NAME}.{arch}.zip'
    )
    return _make_fetcher(version=version, release=release, url=url, arch=arch)


def _build_html_fallback_fetcher() -> CamoufoxFetcher:
    arch = CamoufoxFetcher.get_platform_arch()
    pattern = re.compile(
        rf'href="(?P<href>/daijro/camoufox/releases/download/[^"]+/camoufox-(?P<version>.+)-(?P<release>.+)-{OS_NAME}\.{arch}\.zip)"'
    )
    response = requests.get(RELEASES_URL, headers=_github_headers(), timeout=20)
    response.raise_for_status()

    seen_urls: set[str] = set()
    for match in pattern.finditer(response.text):
        url = f'https://github.com{match.group("href")}'
        if url in seen_urls:
            continue
        seen_urls.add(url)
        return _make_fetcher(
            version=match.group('version'),
            release=match.group('release'),
            url=url,
            arch=arch,
        )

    raise RuntimeError('Unable to find a supported Camoufox release asset from the GitHub releases page.')


def _build_fallback_fetcher() -> CamoufoxFetcher:
    try:
        return _build_html_fallback_fetcher()
    except Exception as exc:
        print(f'GitHub release page scraping failed: {exc}. Falling back to latest redirect URL.')
        return _build_latest_redirect_fetcher()


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

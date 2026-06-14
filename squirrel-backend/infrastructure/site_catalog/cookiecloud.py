import json
import logging
from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from PyCookieCloud import PyCookieCloud
from PyCookieCloud.PyCryptoJS import decrypt

from infrastructure.config.settings import settings
from infrastructure.config.site_config_manager import get_effective_site_catalog
from infrastructure.site_catalog.cookie_files import (
    get_site_cookies_dir,
    get_site_cookies_file_path,
    write_cookie_text_file,
)

logger = logging.getLogger(__name__)


class CookieCloudSyncError(RuntimeError):
    pass


class CookieCloudService:
    @staticmethod
    def _get_cookiecloud_config() -> tuple[str, str, str]:
        url = (settings.COOKIECLOUD_URL or "").strip()
        uuid = (settings.COOKIECLOUD_UUID or "").strip()
        password = (settings.COOKIECLOUD_PASSWORD or "").strip()
        return url, uuid, password

    @staticmethod
    def is_cookiecloud_configured() -> bool:
        url, uuid, password = CookieCloudService._get_cookiecloud_config()
        return bool(url and uuid and password)

    @staticmethod
    def _decode_cookiecloud_response_json(response: requests.Response) -> dict[str, Any]:
        payload = response.content or b""
        attempted_encodings: list[str] = []
        last_error: Exception | None = None

        encodings = [
            response.encoding,
            getattr(response, "apparent_encoding", None),
            "utf-8",
            "utf-8-sig",
            "latin-1",
        ]

        for encoding in encodings:
            if not encoding or encoding in attempted_encodings:
                continue
            attempted_encodings.append(encoding)
            try:
                return json.loads(payload.decode(encoding))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                last_error = exc

        raise CookieCloudSyncError(
            "CookieCloud 响应不是有效的 JSON 数据，请检查服务端编码或反向代理压缩配置",
        ) from last_error

    @staticmethod
    def _fetch_cookiecloud_encrypted_data(url: str, uuid: str) -> str:
        api_root = urlparse(url).path or "/"
        request_path = str(PurePosixPath(api_root, "get", uuid))

        try:
            response = requests.get(urljoin(url, request_path), timeout=15)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise CookieCloudSyncError(f"CookieCloud 请求失败: {exc}") from exc

        payload = CookieCloudService._decode_cookiecloud_response_json(response)
        encrypted_data = payload.get("encrypted")
        if not isinstance(encrypted_data, str) or not encrypted_data.strip():
            raise CookieCloudSyncError("CookieCloud 响应缺少 encrypted 字段")
        return encrypted_data

    @staticmethod
    def fetch_cookiecloud_cookie_data() -> dict[str, Any]:
        url, uuid, password = CookieCloudService._get_cookiecloud_config()
        if not url or not uuid or not password:
            raise CookieCloudSyncError(
                "CookieCloud 未配置，请设置 COOKIECLOUD_URL / COOKIECLOUD_UUID / COOKIECLOUD_PASSWORD",
            )

        client = PyCookieCloud(url=url, uuid=uuid, password=password)
        encrypted_data = CookieCloudService._fetch_cookiecloud_encrypted_data(url=url, uuid=uuid)
        try:
            decrypted_data = decrypt(encrypted_data, client.get_the_key().encode("utf-8")).decode("utf-8")
            payload = json.loads(decrypted_data)
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise CookieCloudSyncError(f"CookieCloud 解密失败: {exc}") from exc

        data = payload.get("cookie_data")
        if not isinstance(data, dict) or not data:
            raise CookieCloudSyncError("CookieCloud 返回为空或解密失败")
        return data

    @staticmethod
    def _normalize_domain(domain: str) -> str:
        if not domain:
            return ""
        d = str(domain).strip()
        if d.startswith("#HttpOnly_"):
            d = d[len("#HttpOnly_"):]
        return d.lstrip(".").lower()

    @staticmethod
    def _domain_matches(cookie_domain: str, site_domain: str) -> bool:
        if not cookie_domain or not site_domain:
            return False
        if cookie_domain == site_domain:
            return True
        return cookie_domain.endswith("." + site_domain)

    @staticmethod
    def _to_int_seconds(value: Any) -> int:
        if value is None or value == "":
            return 0
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _cookie_to_netscape_line(cookie: dict[str, Any]) -> str | None:
        name = cookie.get("name")
        value = cookie.get("value")
        raw_domain = cookie.get("domain")
        if not name or value is None or not raw_domain:
            return None

        domain_clean = str(raw_domain).strip()
        http_only = bool(cookie.get("httpOnly", False))
        host_only = cookie.get("hostOnly")

        include_subdomains: bool
        if host_only is True:
            include_subdomains = False
        elif host_only is False:
            include_subdomains = True
        else:
            include_subdomains = domain_clean.startswith(".")

        domain_no_dot = domain_clean.lstrip(".")
        domain_out = f".{domain_no_dot}" if include_subdomains else domain_no_dot
        if http_only:
            domain_out = f"#HttpOnly_{domain_out}"

        flag_out = "TRUE" if include_subdomains else "FALSE"
        path_out = str(cookie.get("path") or "/")
        secure_out = "TRUE" if bool(cookie.get("secure", False)) else "FALSE"
        expires_out = str(CookieCloudService._to_int_seconds(cookie.get("expirationDate")))

        return "\t".join([domain_out, flag_out, path_out, secure_out, expires_out, str(name), str(value)])

    @staticmethod
    def sync_cookiecloud_to_site_files(site_slug: str | None = None) -> dict[str, Any]:
        cookie_data = CookieCloudService.fetch_cookiecloud_cookie_data()
        catalog = get_effective_site_catalog()

        site_domains: dict[str, list[str]] = {}
        for slug, site_info in catalog.items():
            if site_slug and slug.lower() != site_slug.strip().lower():
                continue
            domains = [
                (d or "").strip().lstrip(".").lower()
                for d in (site_info or {}).get("domains", [])
                if d
            ]
            if domains:
                site_domains[slug] = list(dict.fromkeys(domains))

        if not site_domains:
            raise CookieCloudSyncError("未找到可同步的站点域名配置")

        flattened: list[dict[str, Any]] = []
        for host, entries in (cookie_data or {}).items():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                normalized = dict(entry)
                if not normalized.get("domain"):
                    normalized["domain"] = host
                flattened.append(normalized)

        get_site_cookies_dir().mkdir(parents=True, exist_ok=True)

        result_sites: dict[str, dict[str, Any]] = {}
        for slug, domains in site_domains.items():
            matched: dict[tuple[str, str, str], dict[str, Any]] = {}
            for cookie in flattened:
                raw_domain = cookie.get("domain")
                cookie_domain = CookieCloudService._normalize_domain(raw_domain)
                if not cookie_domain:
                    continue

                if not any(CookieCloudService._domain_matches(cookie_domain, d) for d in domains):
                    continue

                name = str(cookie.get("name") or "").strip()
                path = str(cookie.get("path") or "/")
                if not name:
                    continue

                key = (cookie_domain, path, name)
                existing = matched.get(key)
                if existing is None:
                    matched[key] = cookie
                    continue

                existing_exp = CookieCloudService._to_int_seconds(existing.get("expirationDate"))
                new_exp = CookieCloudService._to_int_seconds(cookie.get("expirationDate"))
                if new_exp > existing_exp:
                    matched[key] = cookie

            if not matched:
                continue

            lines = ["# Netscape HTTP Cookie File"]
            for cookie in matched.values():
                line = CookieCloudService._cookie_to_netscape_line(cookie)
                if line:
                    lines.append(line)

            path = get_site_cookies_file_path(slug)
            write_cookie_text_file(path, "\n".join(lines) + "\n")
            result_sites[slug] = {
                "cookies": max(0, len(lines) - 1),
                "path": str(path),
            }

        synced_at = datetime.now(UTC).isoformat()
        return {
            "synced_at": synced_at,
            "total_cookie_entries": len(flattened),
            "updated_sites": len(result_sites),
            "sites": result_sites,
        }


cookiecloud_service = CookieCloudService()
is_cookiecloud_configured = cookiecloud_service.is_cookiecloud_configured
fetch_cookiecloud_cookie_data = cookiecloud_service.fetch_cookiecloud_cookie_data
sync_cookiecloud_to_site_files = cookiecloud_service.sync_cookiecloud_to_site_files

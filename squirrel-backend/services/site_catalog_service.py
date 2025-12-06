import json
from pathlib import Path
from typing import Dict, List, Any

from core.site_config_manager import apply_site_config_overrides, get_effective_site_catalog
from utils.site_catalog import SiteCatalog


class SiteCatalogService:
    """Handles persisting and validating the editable site catalog."""

    @staticmethod
    def _config_path() -> Path:
        return Path(__file__).resolve().parents[2] / "config" / "sites.json"

    @staticmethod
    def _parse_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return True
        if isinstance(value, (int, float)):
            return bool(value)
        s = str(value).strip().lower()
        if s in {"true", "1", "yes", "y", "on"}:
            return True
        if s in {"false", "0", "no", "n", "off"}:
            return False
        return True

    @staticmethod
    def _normalize_list(values: Any, field_name: str, allow_empty: bool = True) -> List[str]:
        if values is None:
            values = []
        if not isinstance(values, list):
            raise ValueError(f"{field_name} 必须是数组")
        cleaned: List[str] = []
        for item in values:
            text = str(item).strip().lower()
            if text and text not in cleaned:
                cleaned.append(text)
        if not allow_empty and not cleaned:
            raise ValueError(f"{field_name} 不能为空")
        return cleaned

    @staticmethod
    def _normalize_headers(values: Any, field_name: str) -> Dict[str, str]:
        if values is None:
            return {}
        if not isinstance(values, dict):
            raise ValueError(f"{field_name} 必须是对象")
        headers: Dict[str, str] = {}
        for key, val in values.items():
            if key is None:
                continue
            name = str(key).strip()
            if not name:
                continue
            if val is None:
                continue
            headers[name] = str(val)
        return headers

    @classmethod
    def _normalize_proxy(cls, raw: Any) -> Dict[str, Any]:
        if raw is None:
            return {}
        if not isinstance(raw, dict):
            raise ValueError("proxy 必须是对象")
        result: Dict[str, Any] = {}
        float_fields = [
            "connect_timeout",
            "read_timeout",
            "write_timeout",
            "pool_timeout",
            "keepalive_expiry",
        ]
        int_fields = [
            "max_retries",
            "chunk_size",
            "max_connections",
            "max_keepalive_connections",
        ]
        bool_fields = ["enable_http2", "follow_redirects"]
        for field in float_fields:
            value = raw.get(field)
            if value in (None, ""):
                continue
            result[field] = float(value)
        for field in int_fields:
            value = raw.get(field)
            if value in (None, ""):
                continue
            result[field] = int(value)
        for field in bool_fields:
            if field in raw:
                result[field] = cls._parse_bool(raw.get(field))
        return result

    @staticmethod
    def _normalize_rate_limit(raw: Any) -> Dict[str, float]:
        if raw is None:
            return {}
        if not isinstance(raw, dict):
            raise ValueError("rate_limit 必须是对象")
        result: Dict[str, float] = {}
        min_interval = raw.get("min_interval")
        max_interval = raw.get("max_interval")
        if min_interval not in (None, ""):
            result["min_interval"] = float(min_interval)
        if max_interval not in (None, ""):
            result["max_interval"] = float(max_interval)
        return result

    @classmethod
    def _normalize_login(cls, raw: Any) -> Dict[str, Any]:
        if raw is None:
            return {}
        if not isinstance(raw, dict):
            raise ValueError("login 必须是对象")
        result: Dict[str, Any] = {}
        check_url = str(raw.get("check_url") or "").strip()
        if check_url:
            result["check_url"] = check_url
        headers = cls._normalize_headers(raw.get("headers"), "login.headers")
        if headers:
            result["headers"] = headers
        timeout = raw.get("timeout")
        if timeout not in (None, ""):
            result["timeout"] = float(timeout)
        if raw.get("extra_cookies"):
            result["extra_cookies"] = str(raw.get("extra_cookies")).strip()
        return result

    @classmethod
    def _normalize_metadata(cls, raw: Any) -> Dict[str, Any]:
        if raw is None:
            return {}
        if not isinstance(raw, dict):
            raise ValueError("metadata 必须是对象")
        result: Dict[str, Any] = {}
        for key in ("nsfw", "requires_login", "requires_cookies", "player_url_cache"):
            if key in raw:
                result[key] = cls._parse_bool(raw.get(key))
        return result

    @classmethod
    def save_sites(cls, sites: List[dict]) -> Dict[str, dict]:
        if not isinstance(sites, list):
            raise ValueError("sites 必须为数组")

        catalog: Dict[str, dict] = {}
        for idx, raw in enumerate(sites, start=1):
            slug = str(raw.get("slug") or raw.get("name") or "").strip().lower()
            if not slug:
                raise ValueError(f"第 {idx} 项缺少 slug")
            if slug in catalog:
                raise ValueError(f"slug '{slug}' 重复")

            label = str(raw.get("label") or slug).strip() or slug
            domains = cls._normalize_list(raw.get("domains"), f"{slug} 的域名", allow_empty=False)
            aliases = cls._normalize_list(raw.get("aliases"), f"{slug} 的别名")
            enabled = cls._parse_bool(raw.get("enabled", True))

            site_entry: Dict[str, Any] = {
                "label": label,
                "domains": domains,
                "aliases": aliases,
                "enabled": enabled,
            }
            http_section = raw.get("http") or {}
            if raw.get("http") not in (None, {}) and not isinstance(raw.get("http"), dict):
                raise ValueError("http 必须是对象")
            headers = cls._normalize_headers(http_section.get("headers"), f"{slug} 的 HTTP headers")
            if headers:
                site_entry["http"] = {"headers": headers}

            proxy_section = cls._normalize_proxy(raw.get("proxy"))
            if proxy_section:
                site_entry["proxy"] = proxy_section

            login_section = cls._normalize_login(raw.get("login"))
            if login_section:
                site_entry["login"] = login_section

            rate_limit = cls._normalize_rate_limit(raw.get("rate_limit"))
            if rate_limit:
                site_entry["rate_limit"] = rate_limit

            metadata = cls._normalize_metadata(raw.get("metadata"))
            if metadata:
                site_entry["metadata"] = metadata

            test_url = str(raw.get("test_url") or "").strip()
            if test_url:
                site_entry["test_url"] = test_url

            catalog[slug] = site_entry

        config_path = cls._config_path()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps(catalog, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        SiteCatalog.set_catalog(catalog)
        apply_site_config_overrides(catalog)
        return get_effective_site_catalog(catalog)

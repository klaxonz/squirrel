import json
import os
from typing import Dict, List, Optional, Set


class SiteCatalog:
    """
    Loads site configuration from config/sites.json if present, otherwise
    builds a minimal catalog from registered site domains (best-effort).

    sites.json structure example:
    {
      "youtube": {
        "label": "YouTube",
        "domains": ["youtube.com", "youtu.be"],
        "aliases": ["yt"],
        "enabled": true
      }
    }
    """

    _catalog: Dict[str, dict] | None = None
    _catalog_mtime: float | None = None

    @staticmethod
    def _config_path() -> str:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # project root
        root_dir = os.path.dirname(base_dir)
        return os.path.join(root_dir, 'config', 'sites.json')

    @classmethod
    def _get_config_mtime(cls) -> float | None:
        try:
            path = cls._config_path()
            if os.path.exists(path):
                return os.path.getmtime(path)
        except Exception:
            return None
        return None

    @classmethod
    def _load_from_file(cls) -> Optional[Dict[str, dict]]:
        config_path = cls._config_path()
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # normalize
                catalog: Dict[str, dict] = {}
                extra_keys = {'http', 'proxy', 'login', 'rate_limit', 'metadata', 'test_url'}
                for slug, info in (data or {}).items():
                    domains = list({d.strip().lower() for d in info.get('domains', []) if d})
                    aliases = list({a.strip().lower() for a in info.get('aliases', []) if a})
                    normalized_slug = slug.strip().lower()
                    entry: dict = {
                        'label': info.get('label', slug),
                        'domains': domains,
                        'aliases': aliases,
                        'enabled': bool(info.get('enabled', True))
                    }
                    for key in extra_keys:
                        value = info.get(key)
                        if value is not None:
                            entry[key] = value
                    catalog[normalized_slug] = entry
                return catalog
            except Exception:
                return None
        return None

    @classmethod
    def _build_from_registries(cls) -> Dict[str, dict]:
        # best-effort fallback: aggregate domains from various registries
        domains: Set[str] = set()
        try:
            from crawl import (
                get_extractor_registry,
                get_handler_registry,
                get_mpd_registry,
                get_proxy_registry,
                get_subtitles_registry,
                get_subscription_registry,
                get_id_extractor_registry,
            )

            # 收集所有注册表的域名
            registries = [
                get_extractor_registry(),
                get_handler_registry(),
                get_mpd_registry(),
                get_proxy_registry(),
                get_subtitles_registry(),
                get_subscription_registry(),
                get_id_extractor_registry(),
            ]
            
            for reg in registries:
                try:
                    domains.update(reg.get_all_domains())
                except Exception:
                    pass
        except Exception:
            pass

        # Group by top-level host second-level e.g. youtube.com
        catalog: Dict[str, dict] = {}
        for d in sorted(domains):
            parts = d.split('.')
            if len(parts) >= 2:
                slug = parts[-2]
            else:
                slug = d
            item = catalog.setdefault(slug, {
                'label': slug,
                'domains': [],
                'aliases': [],
                'enabled': True
            })
            if d not in item['domains']:
                item['domains'].append(d)
        return catalog

    @classmethod
    def get_catalog(cls) -> Dict[str, dict]:
        config_mtime = cls._get_config_mtime()
        should_reload = cls._catalog is None or config_mtime != cls._catalog_mtime

        if should_reload:
            file_catalog = cls._load_from_file()
            if file_catalog is not None:
                cls._catalog = file_catalog
                cls._catalog_mtime = config_mtime
            else:
                cls._catalog = cls._build_from_registries()
                cls._catalog_mtime = config_mtime
        return cls._catalog

    @classmethod
    def set_catalog(cls, catalog: Dict[str, dict]) -> None:
        """Replace the in-memory catalog (e.g. after editing via API)."""
        cls._catalog = catalog
        cls._catalog_mtime = cls._get_config_mtime()

    @classmethod
    def reload(cls) -> Dict[str, dict]:
        """Force reloading catalog from disk or registries."""
        cls._catalog = None
        cls._catalog_mtime = None
        return cls.get_catalog()

    @classmethod
    def get_all_domains(cls) -> List[str]:
        domains: List[str] = []
        for info in cls.get_catalog().values():
            if info.get('enabled', True):
                domains.extend(info.get('domains', []))
        # unique keep order
        seen: Set[str] = set()
        ordered = []
        for d in domains:
            if d not in seen:
                seen.add(d)
                ordered.append(d)
        return ordered

    @classmethod
    def resolve_domains(cls, key: Optional[str]) -> List[str]:
        """
        Resolve a site slug or alias to its configured domain list.
        Fallback: substring matching against all domains.
        """
        if not key:
            return []
        k = key.strip().lower()
        catalog = cls.get_catalog()
        # exact slug
        if k in catalog and catalog[k].get('enabled', True):
            return catalog[k].get('domains', [])
        # alias
        for slug, info in catalog.items():
            if not info.get('enabled', True):
                continue
            aliases = [a.lower() for a in info.get('aliases', [])]
            if k in aliases:
                return info.get('domains', [])
        # substring match
        all_domains = cls.get_all_domains()
        matched = [d for d in all_domains if k in d.lower()]
        return matched

    @classmethod
    def find_site_by_domain(cls, domain: Optional[str]) -> tuple[Optional[str], Optional[dict]]:
        """Find site slug and catalog entry by domain (supports subdomain match)."""
        if not domain:
            return None, None
        domain_lower = str(domain).split(":")[0].strip().lower()
        catalog = cls.get_catalog() or {}
        for slug, info in catalog.items():
            domains = info.get("domains") or []
            for d in domains:
                d_lower = str(d).strip().lower()
                if not d_lower:
                    continue
                if domain_lower == d_lower or domain_lower.endswith(f".{d_lower}"):
                    return slug, info
        return None, None

    @classmethod
    def is_site_enabled(cls, site: Optional[str] = None, domain: Optional[str] = None) -> bool:
        """Check whether a site is enabled via slug or domain lookup."""
        if domain:
            _, info = cls.find_site_by_domain(domain)
            if info is not None:
                return info.get("enabled", True)

        if site:
            catalog = cls.get_catalog() or {}
            info = catalog.get(site.strip().lower())
            if info is not None:
                return info.get("enabled", True)

        return True

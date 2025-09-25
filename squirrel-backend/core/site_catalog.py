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

    @classmethod
    def _load_from_file(cls) -> Optional[Dict[str, dict]]:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # project root
        root_dir = os.path.dirname(base_dir)
        config_path = os.path.join(root_dir, 'config', 'sites.json')
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # normalize
                catalog: Dict[str, dict] = {}
                for slug, info in (data or {}).items():
                    domains = list({d.strip().lower() for d in info.get('domains', []) if d})
                    aliases = list({a.strip().lower() for a in info.get('aliases', []) if a})
                    catalog[slug.strip().lower()] = {
                        'label': info.get('label', slug),
                        'domains': domains,
                        'aliases': aliases,
                        'enabled': bool(info.get('enabled', True))
                    }
                return catalog
            except Exception:
                return None
        return None

    @classmethod
    def _build_from_registries(cls) -> Dict[str, dict]:
        # best-effort fallback: aggregate domains from various registries
        registries = []
        try:
            from crawl import (
                HandlerRegistry,
                MpdRegistry,
                ProxyRegistry,
                MetaRegistry,
                SubtitlesRegistry,
                SubscriptionRegistry,
                IdExtractorRegistry,
            )

            registries.extend([
                HandlerRegistry,
                MpdRegistry,
                ProxyRegistry,
                MetaRegistry,
                SubtitlesRegistry,
                SubscriptionRegistry,
                IdExtractorRegistry,
            ])
        except Exception:
            pass

        domains: Set[str] = set()
        for reg in registries:
            try:
                domains.update(reg.get_supported_domains())
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
        if cls._catalog is None:
            file_catalog = cls._load_from_file()
            if file_catalog is not None:
                cls._catalog = file_catalog
            else:
                cls._catalog = cls._build_from_registries()
        return cls._catalog

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



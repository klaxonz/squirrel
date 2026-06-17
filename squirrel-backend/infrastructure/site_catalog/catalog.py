import json
import os
from pathlib import Path

from infrastructure.site_catalog.icons import build_site_icon_url, resolve_site_icon_path
from infrastructure.site_runtimes.models import SiteRuntimeSnapshot
from infrastructure.site_runtimes.ports import get_runtime_snapshot
from infrastructure.site_runtimes.runtime_models import SiteRuntimeManifest


class SiteCatalog:
    """Loads site configuration and runtime site metadata.

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

    _override_catalog: dict[str, dict] | None = None
    _override_catalog_mtime: float | None = None

    @staticmethod
    def _config_path() -> str:
        repo_root = Path(__file__).resolve().parents[3]
        return str(repo_root / "config" / "sites.json")

    @classmethod
    def _get_config_mtime(cls) -> float | None:
        try:
            path = cls._config_path()
            if os.path.exists(path):
                return os.path.getmtime(path)
        except OSError:
            return None
        return None

    @classmethod
    def _normalize_catalog_entry(cls, slug: str, info: dict | None) -> dict:
        info = dict(info or {})
        domains = list({d.strip().lower() for d in info.get("domains", []) if d})
        aliases = list({a.strip().lower() for a in info.get("aliases", []) if a})
        entry: dict = {
            "label": info.get("label", slug),
            "domains": domains,
            "aliases": aliases,
            "enabled": bool(info.get("enabled", True)),
        }
        extra_keys = {"http", "proxy", "login", "rate_limit", "metadata", "test_url", "icon_url", "cookie", "features"}
        for key in extra_keys:
            value = info.get(key)
            if value is not None:
                entry[key] = value
        return entry

    @classmethod
    def _normalize_override_entry(cls, slug: str, info: dict | None) -> dict:
        info = dict(info or {})
        entry: dict = {}

        if "label" in info:
            label = str(info.get("label") or "").strip()
            if label:
                entry["label"] = label

        if "domains" in info:
            entry["domains"] = list({d.strip().lower() for d in info.get("domains", []) if d})

        if "aliases" in info:
            entry["aliases"] = list({a.strip().lower() for a in info.get("aliases", []) if a})

        if "enabled" in info:
            entry["enabled"] = bool(info.get("enabled", True))

        extra_keys = {"http", "proxy", "login", "rate_limit", "metadata", "test_url", "icon_url", "cookie", "features"}
        for key in extra_keys:
            if key not in info:
                continue
            value = info.get(key)
            if value is not None:
                entry[key] = value

        return entry

    @classmethod
    def load_override_catalog(cls) -> dict[str, dict] | None:
        config_path = cls._config_path()
        if os.path.exists(config_path):
            try:
                with open(config_path, encoding="utf-8") as f:
                    data = json.load(f)
                catalog: dict[str, dict] = {}
                for slug, site_info in (data or {}).items():
                    normalized_slug = slug.strip().lower()
                    catalog[normalized_slug] = cls._normalize_override_entry(normalized_slug, site_info)
                return catalog
            except (OSError, ValueError):
                return None
        return None

    @classmethod
    def build_runtime_site_catalog(cls, snapshot: SiteRuntimeSnapshot | None = None) -> dict[str, dict]:
        catalog: dict[str, dict] = {}
        snapshot = snapshot or get_runtime_snapshot()
        for record in snapshot.records:
            manifest = SiteRuntimeManifest.from_dict(record.manifest)
            for site in manifest.sites:
                slug = site.site_name.strip().lower()
                defaults = dict(site.metadata or {})
                item = catalog.setdefault(slug, {
                    "label": defaults.get("label") or site.site_name,
                    "domains": [],
                    "aliases": [],
                    "enabled": record.enabled,
                    "features": [],
                })
                item["enabled"] = bool(defaults.get("enabled", item.get("enabled", True))) and record.enabled
                item["label"] = defaults.get("label") or item.get("label") or site.site_name
                if site.test_url:
                    item["test_url"] = site.test_url
                default_aliases = [str(alias).strip().lower() for alias in list(defaults.get("aliases") or []) if alias]
                existing_aliases = set(item.get("aliases") or [])
                for alias in default_aliases:
                    if alias not in existing_aliases:
                        item.setdefault("aliases", []).append(alias)
                        existing_aliases.add(alias)
                for key in ("http", "proxy", "login", "rate_limit", "cookie", "metadata", "icon_url"):
                    value = defaults.get(key)
                    if value is not None:
                        item[key] = value
                if not item.get("icon_url") and resolve_site_icon_path(site.site_name):
                    item["icon_url"] = build_site_icon_url(site.site_name)
                existing_features = set(item.get("features") or [])
                for feature in site.features:
                    if feature not in existing_features:
                        item.setdefault("features", []).append(feature)
                        existing_features.add(feature)
                for domain in site.domains:
                    normalized = str(domain).strip().lower()
                    if normalized and normalized not in item["domains"]:
                        item["domains"].append(normalized)
        return catalog

    @classmethod
    def get_catalog(cls) -> dict[str, dict]:
        config_mtime = cls._get_config_mtime()
        should_reload = cls._override_catalog is None or config_mtime != cls._override_catalog_mtime

        if should_reload:
            file_catalog = cls.load_override_catalog()
            if file_catalog is not None:
                cls._override_catalog = file_catalog
                cls._override_catalog_mtime = config_mtime
            else:
                cls._override_catalog = {}
                cls._override_catalog_mtime = config_mtime
        return cls._override_catalog

    @classmethod
    def set_override_catalog(cls, catalog: dict[str, dict]) -> None:
        """Replace the in-memory override catalog (e.g. after editing via API)."""
        cls._override_catalog = dict(catalog or {})
        cls._override_catalog_mtime = cls._get_config_mtime()

    @classmethod
    def set_catalog(cls, catalog: dict[str, dict]) -> None:
        cls.set_override_catalog(catalog)

    @classmethod
    def reload(cls) -> dict[str, dict]:
        """Force reloading override catalog from disk."""
        cls._override_catalog = None
        cls._override_catalog_mtime = None
        return cls.get_catalog()

    @classmethod
    def _get_effective_catalog(cls) -> dict[str, dict]:
        from infrastructure.runtime.site_config_manager import get_effective_site_catalog

        return get_effective_site_catalog()

    @classmethod
    def _load_from_file(cls) -> dict[str, dict] | None:
        return cls.load_override_catalog()

    @classmethod
    def _build_from_manifests(cls, snapshot: SiteRuntimeSnapshot | None = None) -> dict[str, dict]:
        return cls.build_runtime_site_catalog(snapshot=snapshot)

    @classmethod
    def get_all_domains(cls) -> list[str]:
        domains: list[str] = []
        for info in cls._get_effective_catalog().values():
            if info.get("enabled", True):
                domains.extend(info.get("domains", []))
        # unique keep order
        seen: set[str] = set()
        ordered = []
        for d in domains:
            if d not in seen:
                seen.add(d)
                ordered.append(d)
        return ordered

    @classmethod
    def resolve_domains(cls, key: str | None) -> list[str]:
        """Resolve a site slug or alias to its configured domain list.

        Also supports substring matching against all domains.
        """
        if not key:
            return []
        k = key.strip().lower()
        catalog = cls._get_effective_catalog()
        # exact slug
        if k in catalog and catalog[k].get("enabled", True):
            return catalog[k].get("domains", [])
        # alias
        for slug, site_info in catalog.items():
            if not site_info.get("enabled", True):
                continue
            aliases = [a.lower() for a in site_info.get("aliases", [])]
            if k in aliases:
                return site_info.get("domains", [])
        # substring match
        all_domains = cls.get_all_domains()
        matched = [d for d in all_domains if k in d.lower()]
        return matched

    @classmethod
    def expand_site_filter_values(cls, key: str | None) -> list[str]:
        """Expand a site filter into all equivalent identifiers used in storage/query layers.

        Examples:
        - "youtube" -> ["youtube", "youtube.com", "youtu.be"]
        - "youtube.com" -> ["youtube.com", "youtube"]

        """
        if not key:
            return []

        normalized_key = str(key).strip().lower()
        if not normalized_key:
            return []

        catalog = cls._get_effective_catalog() or {}
        values: list[str] = []
        seen: set[str] = set()

        def add(value: str | None) -> None:
            normalized = str(value or "").strip().lower()
            if not normalized or normalized in seen:
                return
            seen.add(normalized)
            values.append(normalized)

        add(normalized_key)

        for domain in cls.resolve_domains(normalized_key):
            add(domain)

        if normalized_key in catalog:
            for domain in catalog[normalized_key].get("domains", []):
                add(domain)

        for slug, site_info in catalog.items():
            aliases = [str(alias or "").strip().lower() for alias in site_info.get("aliases", []) if alias]
            if normalized_key == slug or normalized_key in aliases:
                add(slug)
                for domain in site_info.get("domains", []):
                    add(domain)

        site_slug, info = cls.find_site_by_domain(normalized_key)
        if site_slug:
            add(site_slug)
            for domain in (info or {}).get("domains", []):
                add(domain)

        return values

    @classmethod
    def find_site_by_domain(cls, domain: str | None) -> tuple[str | None, dict | None]:
        """Find site slug and catalog entry by domain (supports subdomain match)."""
        if not domain:
            return None, None
        domain_lower = str(domain).split(":")[0].strip().lower()
        catalog = cls._get_effective_catalog() or {}
        for slug, site_info in catalog.items():
            domains = site_info.get("domains") or []
            for d in domains:
                d_lower = str(d).strip().lower()
                if not d_lower:
                    continue
                if domain_lower == d_lower or domain_lower.endswith(f".{d_lower}"):
                    return slug, site_info
        return None, None

    @classmethod
    def is_site_enabled(cls, site: str | None = None, domain: str | None = None) -> bool:
        """Check whether a site is enabled via slug or domain lookup."""
        if domain:
            _, info = cls.find_site_by_domain(domain)
            if info is not None:
                return info.get("enabled", True)

        if site:
            catalog = cls._get_effective_catalog() or {}
            info = catalog.get(site.strip().lower())
            if info is not None:
                return info.get("enabled", True)

        return True

    @classmethod
    def get_enabled_site_names(cls) -> set[str]:
        """Return enabled site slugs from the effective catalog."""
        catalog = cls._get_effective_catalog() or {}
        return {
            str(slug).strip().lower()
            for slug, site_info in catalog.items()
            if str(slug).strip() and site_info.get("enabled", True)
        }



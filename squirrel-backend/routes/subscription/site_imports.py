from services.site_catalog.catalog import SiteCatalog


def normalize_site_name(site: str) -> str:
    return str(site or '').strip().lower()


def get_normalized_supported_sites(supported_sites: list[str]) -> list[str]:
    normalized_sites: list[str] = []
    seen: set[str] = set()
    for site in supported_sites:
        normalized_site = normalize_site_name(site)
        if not normalized_site or normalized_site in seen:
            continue
        seen.add(normalized_site)
        normalized_sites.append(normalized_site)
    return normalized_sites


def get_supported_site_set(supported_sites: list[str]) -> set[str]:
    return set(get_normalized_supported_sites(supported_sites))


def get_enabled_import_sites(supported_sites: list[str]) -> list[str]:
    enabled_sites = SiteCatalog.get_enabled_site_names()
    return [site for site in get_normalized_supported_sites(supported_sites) if site in enabled_sites]

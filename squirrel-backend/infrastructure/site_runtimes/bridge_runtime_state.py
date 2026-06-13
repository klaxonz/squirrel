from __future__ import annotations


def configure_backend_runtime_state() -> None:
    try:
        from infrastructure.site_catalog.cloudflare_bypass import get_default_client
        from infrastructure.site_catalog.runtime_http import set_cloudflare_bypass_client

        set_cloudflare_bypass_client(get_default_client())
    except Exception:
        # process boundary -- optional runtime init, must not crash the subprocess
        pass
    try:
        from infrastructure.site_catalog.cookies import resolve_cookie_file_for_url, resolve_cookie_match_domain_for_url
        from infrastructure.site_catalog.runtime_http import set_cookie_domain_resolver, set_cookie_file_resolver

        set_cookie_file_resolver(resolve_cookie_file_for_url)
        set_cookie_domain_resolver(resolve_cookie_match_domain_for_url)
    except Exception:
        # process boundary -- optional runtime init, must not crash the subprocess
        pass
    try:
        from infrastructure.config.site_config_manager import apply_crawl_rate_limit_overrides

        apply_crawl_rate_limit_overrides()
    except Exception:
        # process boundary -- optional runtime init, must not crash the subprocess
        pass

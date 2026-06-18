import importlib

import crawl
import pytest

LEGACY_EXPORTS = {
    "PluginDescriptor",
    "create_plugin",
    "discover_components",
    "register_plugin_components",
    "PluginRegistry",
    "ComponentFactory",
    "RegistryManager",
    "get_registry_manager",
    "reset_registry_manager",
    "get_extractor_registry",
    "get_subscription_registry",
    "get_importer_registry",
    "get_login_checker_registry",
    "reset_all_registries",
    "ExtractorFactory",
    "get_extractor_factory",
    "register_extractor",
    "register_subscription",
    "register_user_subscription_importer",
    "register_login_checker",
    "BaseExtractor",
    "Downloader",
    "DownloaderFactory",
    "get_downloader_registry",
    "get_downloader_factory",
    "register_downloader",
    "get_handler_registry",
    "register_handler",
    "get_mpd_registry",
    "register_mpd",
    "get_subtitles_registry",
    "register_subtitles",
    "get_proxy_registry",
    "register_proxy",
    "get_proxy_config_registry",
    "register_site_config",
    "create_site_config",
    "get_id_extractor_registry",
    "register_id_extractor",
}


@pytest.mark.parametrize("name", sorted(LEGACY_EXPORTS))
def test_crawl_package_does_not_export_legacy_runtime_v1_symbols(name):
    assert not hasattr(crawl, name)


@pytest.mark.parametrize("module_name", ["crawl.registry", "crawl.downloader", "crawl.registries"])
def test_removed_legacy_runtime_modules_are_not_importable(module_name):
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(module_name)

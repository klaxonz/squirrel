from __future__ import annotations

import hashlib
import json
import multiprocessing
import sys
import threading
from collections.abc import Iterable, Mapping
from contextlib import suppress
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from queue import Empty
from time import monotonic
from typing import Any
from uuid import uuid4

from infrastructure.runtime.import_paths import install_runtime_import_paths
from infrastructure.site_catalog.config_path import get_site_catalog_config_path


@dataclass(frozen=True)
class SitePluginError:
    message: str
    details: dict[str, Any]
    retryable: bool = False
    code: str | None = None


@dataclass(frozen=True)
class SitePluginResult:
    ok: bool
    data: Any = None
    error: SitePluginError | None = None
    retryable: bool = False


@dataclass(frozen=True)
class _PluginDefinition:
    package_dir: str
    module_name: str


_PLUGIN_DEFINITIONS = {
    'bilibili': _PluginDefinition('bilibili', 'squirrel_bilibili.runtime'),
    'youtube': _PluginDefinition('youtube', 'squirrel_youtube.runtime'),
}

_PLUGIN_CATEGORY_ERROR_CODES = {
    'auth': 'PLUGIN_AUTH_REQUIRED',
    'network': 'PLUGIN_NETWORK_ERROR',
    'parse': 'PLUGIN_PARSE_ERROR',
    'rate_limit': 'PLUGIN_NETWORK_ERROR',
}


def _stringify_error_code(value: Any) -> str | None:
    value = getattr(value, 'value', value)
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _plugin_failure_response(
    *,
    code: str,
    message: str,
    retryable: bool,
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        'ok': False,
        'data': None,
        'error': {
            'code': code,
            'message': message,
            'details': dict(details or {}),
            'retryable': retryable,
        },
        'retryable': retryable,
    }


def _serialize_plugin_exception(exc: Exception) -> dict[str, Any]:
    serialized: Mapping[str, Any] = {}
    serializer = getattr(exc, 'to_dict', None)
    if callable(serializer):
        with suppress(Exception):
            candidate = serializer()
            if isinstance(candidate, Mapping):
                serialized = candidate

    raw_details = serialized.get('details') or serialized.get('context')
    if raw_details is None:
        raw_details = getattr(exc, 'details', None) or getattr(exc, 'context', None)
    details = dict(raw_details) if isinstance(raw_details, Mapping) else {}
    details.setdefault('exception_type', type(exc).__name__)

    category = _stringify_error_code(serialized.get('category') or getattr(exc, 'category', None))
    if category:
        details.setdefault('error_category', category)

    retry_after_seconds = serialized.get('retry_after_seconds')
    if retry_after_seconds is None:
        retry_after_seconds = getattr(exc, 'retry_after_seconds', None)
    if retry_after_seconds is None:
        retry_after_seconds = getattr(exc, 'retry_after', None)
    if retry_after_seconds is not None:
        details.setdefault('retry_after_seconds', retry_after_seconds)

    code = (
        _stringify_error_code(serialized.get('code'))
        or _stringify_error_code(getattr(exc, 'code', None))
        or _stringify_error_code(serialized.get('error_type'))
        or _stringify_error_code(getattr(exc, 'error_type', None))
        or _PLUGIN_CATEGORY_ERROR_CODES.get(category or '')
        or 'PLUGIN_CRASHED'
    )
    default_retryable = not isinstance(exc, (ValueError, TypeError, AttributeError, KeyError))
    retryable = bool(serialized.get('retryable', getattr(exc, 'retryable', default_retryable)))
    message = str(serialized.get('message') or exc)
    return _plugin_failure_response(
        code=code,
        message=message,
        retryable=retryable,
        details=details,
    )


class _PluginProcessStartError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        error_type: str,
        retryable: bool,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.retryable = retryable
        self.details = dict(details or {})


def _plugin_process_main(repo_root: str, slug: str, requests, responses) -> None:
    """Run one site runtime behind a killable process boundary."""
    plugin = None
    try:
        from infrastructure.runtime.site_config_manager import apply_site_config_overrides
        from infrastructure.site_catalog.cookies import (
            resolve_cookie_file_for_url,
            resolve_cookie_match_domain_for_url,
        )
        from infrastructure.site_catalog.runtime_http import (
            set_cloudflare_bypass_client,
            set_cookie_domain_resolver,
            set_cookie_file_resolver,
        )

        apply_site_config_overrides()
        set_cookie_file_resolver(resolve_cookie_file_for_url)
        set_cookie_domain_resolver(resolve_cookie_match_domain_for_url)
        try:
            from infrastructure.site_catalog.cloudflare_bypass import get_default_client

            set_cloudflare_bypass_client(get_default_client())
        except Exception:
            set_cloudflare_bypass_client(None)
        registry = SitePluginRegistry(repo_root=Path(repo_root))
        plugin = registry._load_plugin(slug)
        plugin.start({})
        responses.put({'type': 'ready'})
        while True:
            request = requests.get()
            if request is None:
                break
            request_id = str(request['request_id'])
            try:
                response = plugin.invoke(request['capability'], dict(request.get('payload') or {}))
                data = response.to_dict() if hasattr(response, 'to_dict') else response
                responses.put({'type': 'result', 'request_id': request_id, 'response': data})
            except Exception as exc:  # isolated plugin boundary
                responses.put(
                    {
                        'type': 'result',
                        'request_id': request_id,
                        'response': _serialize_plugin_exception(exc),
                    },
                )
    except Exception as exc:  # startup boundary
        responses.put({'type': 'startup_error', 'error': _serialize_plugin_exception(exc)['error']})
    finally:
        if plugin is not None:
            with suppress(Exception):
                plugin.stop()


class _PluginProcessHost:
    def __init__(self, repo_root: Path, slug: str, *, startup_timeout_seconds: float = 30.0) -> None:
        self._repo_root = repo_root
        self._slug = slug
        self._startup_timeout_seconds = startup_timeout_seconds
        self._context = multiprocessing.get_context('spawn')
        self._lock = threading.Lock()
        self._process = None
        self._requests = None
        self._responses = None
        self._config_revision: str | None = None

    def start(self) -> None:
        with self._lock:
            self._ensure_started()

    def restart(self) -> None:
        """Atomically replace this site's process between capability calls."""
        with self._lock:
            self._stop_locked(deadline=monotonic() + 5.0)
            self._ensure_started()

    def invoke(self, capability: str, payload: dict[str, Any], timeout_seconds: float) -> dict[str, Any]:
        timeout_seconds = max(0.001, timeout_seconds)
        timeout_ms = max(1, int(timeout_seconds * 1000))
        deadline = monotonic() + timeout_seconds
        if not self._lock.acquire(timeout=max(0.0, deadline - monotonic())):
            return _plugin_failure_response(
                code='PLUGIN_TIMEOUT',
                message=f'Site plugin exceeded its {timeout_ms}ms deadline while waiting for capacity',
                retryable=True,
                details={'phase': 'queue_wait', 'timeout_ms': timeout_ms},
            )
        try:
            if monotonic() >= deadline:
                return self._timeout_response(phase='queue_wait', timeout_ms=timeout_ms)
            try:
                self._ensure_started(deadline=deadline, timeout_ms=timeout_ms)
            except _PluginProcessStartError as exc:
                return _serialize_plugin_exception(exc)
            except Exception as exc:  # process/queue bootstrap boundary
                self._terminate(deadline=deadline)
                return _serialize_plugin_exception(
                    _PluginProcessStartError(
                        f'Site plugin startup failed: site={self._slug}, error={exc}',
                        error_type='PLUGIN_CRASHED',
                        retryable=True,
                        details={'phase': 'startup', 'exception_type': type(exc).__name__},
                    )
                )
            if monotonic() >= deadline:
                return self._timeout_response(phase='startup', timeout_ms=timeout_ms)
            request_id = uuid4().hex
            try:
                self._requests.put(
                    {
                        'request_id': request_id,
                        'capability': capability,
                        'payload': payload,
                    },
                )
            except Exception as exc:
                self._terminate(deadline=deadline)
                return _plugin_failure_response(
                    code='PLUGIN_CRASHED',
                    message=f'Failed to dispatch capability to site plugin: site={self._slug}',
                    retryable=True,
                    details={'phase': 'dispatch', 'exception_type': type(exc).__name__},
                )
            while True:
                remaining = deadline - monotonic()
                if remaining <= 0:
                    self._terminate(deadline=deadline)
                    return self._timeout_response(phase='invoke', timeout_ms=timeout_ms)
                try:
                    message = self._responses.get(timeout=min(0.25, remaining))
                    break
                except Empty:
                    if self._process is None or not self._process.is_alive():
                        self._terminate(deadline=deadline)
                        return _plugin_failure_response(
                            code='PLUGIN_CRASHED',
                            message=f'Site plugin process exited unexpectedly: site={self._slug}',
                            retryable=True,
                            details={'phase': 'invoke'},
                        )
                except (EOFError, OSError, ValueError) as exc:
                    self._terminate(deadline=deadline)
                    return _plugin_failure_response(
                        code='PLUGIN_CRASHED',
                        message=f'Lost communication with site plugin: site={self._slug}',
                        retryable=True,
                        details={'phase': 'invoke', 'exception_type': type(exc).__name__},
                    )
            if (
                not isinstance(message, Mapping)
                or message.get('type') != 'result'
                or message.get('request_id') != request_id
                or not isinstance(message.get('response'), Mapping)
            ):
                self._terminate(deadline=deadline)
                return _plugin_failure_response(
                    code='PLUGIN_BAD_RESPONSE',
                    message=f'Invalid site plugin response: site={self._slug}',
                    retryable=False,
                    details={'phase': 'invoke'},
                )
            return dict(message['response'])
        finally:
            self._lock.release()

    def stop(self) -> None:
        with self._lock:
            self._stop_locked(deadline=monotonic() + 5.0)

    def _ensure_started(self, *, deadline: float | None = None, timeout_ms: int | None = None) -> None:
        if deadline is None:
            deadline = monotonic() + self._startup_timeout_seconds
        reported_timeout_ms = timeout_ms or max(1, int(self._startup_timeout_seconds * 1000))

        while True:
            target_revision = self._read_site_config_revision()
            if self._process is not None and self._process.is_alive():
                if self._config_revision == target_revision:
                    return
                # The config file is shared by web and worker processes. Refresh
                # lazily here so every process observes API-side updates.
                self._stop_locked(deadline=deadline)
            else:
                self._terminate(deadline=deadline)

            if monotonic() >= deadline:
                raise self._startup_timeout_error(reported_timeout_ms)

            try:
                self._requests = self._context.Queue()
                self._responses = self._context.Queue()
                self._process = self._context.Process(
                    target=_plugin_process_main,
                    args=(str(self._repo_root), self._slug, self._requests, self._responses),
                    name=f'site-plugin-{self._slug}',
                    daemon=True,
                )
                self._process.start()
            except Exception as exc:
                self._terminate(deadline=deadline)
                raise _PluginProcessStartError(
                    f'Site plugin process could not start: site={self._slug}, error={exc}',
                    error_type='PLUGIN_CRASHED',
                    retryable=True,
                    details={'phase': 'startup', 'exception_type': type(exc).__name__},
                ) from exc

            message = self._wait_for_startup(deadline=deadline, timeout_ms=reported_timeout_ms)
            if not isinstance(message, Mapping):
                self._terminate(deadline=deadline)
                raise _PluginProcessStartError(
                    f'Site plugin returned an invalid startup response: site={self._slug}',
                    error_type='PLUGIN_BAD_RESPONSE',
                    retryable=False,
                    details={'phase': 'startup'},
                )
            if message.get('type') != 'ready':
                self._terminate(deadline=deadline)
                error = message.get('error') if isinstance(message.get('error'), dict) else {}
                details = error.get('details') if isinstance(error.get('details'), dict) else {}
                details = {'phase': 'startup', **details}
                raise _PluginProcessStartError(
                    f'Site plugin startup failed: site={self._slug}, error={error.get("message") or "unknown"}',
                    error_type=_stringify_error_code(error.get('code')) or 'PLUGIN_CRASHED',
                    retryable=bool(error.get('retryable', False)),
                    details=details,
                )

            current_revision = self._read_site_config_revision()
            if current_revision == target_revision:
                self._config_revision = current_revision
                return
            self._stop_locked(deadline=deadline)

    def _wait_for_startup(self, *, deadline: float, timeout_ms: int) -> dict[str, Any]:
        startup_deadline = min(deadline, monotonic() + self._startup_timeout_seconds)
        while True:
            remaining = startup_deadline - monotonic()
            if remaining <= 0:
                self._terminate(deadline=deadline)
                raise self._startup_timeout_error(timeout_ms)
            try:
                return self._responses.get(timeout=min(0.25, remaining))
            except Empty:
                if self._process is None or not self._process.is_alive():
                    self._terminate(deadline=deadline)
                    raise _PluginProcessStartError(
                        f'Site plugin process exited during startup: site={self._slug}',
                        error_type='PLUGIN_CRASHED',
                        retryable=True,
                        details={'phase': 'startup'},
                    ) from None
            except (EOFError, OSError, ValueError) as exc:
                self._terminate(deadline=deadline)
                raise _PluginProcessStartError(
                    f'Lost communication while starting site plugin: site={self._slug}',
                    error_type='PLUGIN_CRASHED',
                    retryable=True,
                    details={'phase': 'startup', 'exception_type': type(exc).__name__},
                ) from exc

    def _startup_timeout_error(self, timeout_ms: int) -> _PluginProcessStartError:
        return _PluginProcessStartError(
            f'Site plugin startup exceeded its deadline: site={self._slug}',
            error_type='PLUGIN_TIMEOUT',
            retryable=True,
            details={'phase': 'startup', 'timeout_ms': timeout_ms},
        )

    def _timeout_response(self, *, phase: str, timeout_ms: int) -> dict[str, Any]:
        return _plugin_failure_response(
            code='PLUGIN_TIMEOUT',
            message=f'Site plugin exceeded its {timeout_ms}ms deadline',
            retryable=True,
            details={'phase': phase, 'timeout_ms': timeout_ms},
        )

    def _read_site_config_revision(self) -> str:
        config_path = get_site_catalog_config_path(self._repo_root)
        try:
            raw = config_path.read_bytes()
        except FileNotFoundError:
            raw = b''
        except OSError as exc:
            return f'unreadable:{type(exc).__name__}:{exc.errno}'

        try:
            catalog = json.loads(raw.decode('utf-8')) if raw else {}
            site_config = catalog.get(self._slug) if isinstance(catalog, dict) else None
            relevant = json.dumps(
                site_config,
                ensure_ascii=False,
                sort_keys=True,
                separators=(',', ':'),
            ).encode('utf-8')
        except (UnicodeDecodeError, ValueError, TypeError):
            relevant = raw
        return hashlib.sha256(relevant).hexdigest()

    def _stop_locked(self, *, deadline: float) -> None:
        if self._process is not None and self._process.is_alive():
            with suppress(Exception):
                self._requests.put(None)
            self._process.join(timeout=max(0.0, min(5.0, deadline - monotonic())))
        self._terminate(deadline=deadline)

    def _terminate(self, *, deadline: float | None = None) -> None:
        process = self._process
        if process is not None and process.is_alive():
            process.terminate()
            join_timeout = 5.0 if deadline is None else max(0.0, min(5.0, deadline - monotonic()))
            process.join(timeout=join_timeout)
            if process.is_alive() and hasattr(process, 'kill'):
                process.kill()
                kill_timeout = 2.0 if deadline is None else max(0.0, min(2.0, deadline - monotonic()))
                process.join(timeout=kill_timeout)
        for channel in (self._requests, self._responses):
            if channel is not None:
                with suppress(Exception):
                    if hasattr(channel, 'cancel_join_thread'):
                        channel.cancel_join_thread()
                    channel.close()
                    channel.join_thread()
        self._process = None
        self._requests = None
        self._responses = None
        self._config_revision = None


class SitePluginRegistry:
    def __init__(self, repo_root: Path | None = None) -> None:
        self._repo_root = repo_root or Path(__file__).resolve().parents[3]
        self._plugins: dict[str, Any] = {}
        self._process_hosts: dict[str, _PluginProcessHost] = {}
        self._registry_lock = threading.RLock()

    @property
    def _runtimes_root(self) -> Path:
        return self._repo_root / 'squirrel-site-runtimes'

    def _install_import_paths(self) -> None:
        install_runtime_import_paths()
        paths = [self._runtimes_root / 'shared']
        paths.extend(self._runtimes_root / item.package_dir / 'src' for item in _PLUGIN_DEFINITIONS.values())
        for path in reversed(paths):
            text = str(path)
            if text not in sys.path:
                sys.path.insert(0, text)

    def _load_plugin(self, site_name: str):
        slug = site_name.strip().lower()
        with self._registry_lock:
            plugin = self._plugins.get(slug)
            if plugin is not None:
                return plugin

            definition = _PLUGIN_DEFINITIONS[slug]
            self._install_import_paths()
            module = import_module(definition.module_name)
            plugin = module.get_site_runtime()
            self._plugins[slug] = plugin
            return plugin

    def start_all(self) -> None:
        try:
            for site_name in _PLUGIN_DEFINITIONS:
                manifest = self._load_plugin(site_name).manifest()
                self._get_process_host(site_name, manifest).start()
        except Exception:
            with suppress(Exception):
                self.stop_all()
            raise

    def stop_all(self) -> None:
        with self._registry_lock:
            hosts = list(self._process_hosts.values())
            self._process_hosts.clear()
        first_error = None
        for host in hosts:
            try:
                host.stop()
            except Exception as exc:
                first_error = first_error or exc
        if first_error is not None:
            raise first_error

    def refresh_sites(self, site_names: Iterable[str]) -> None:
        """Restart active hosts for changed sites under each host's invocation lock.

        Other application processes detect the same file-backed update through
        the per-site revision check in ``_PluginProcessHost.invoke``.
        """
        normalized_sites = {
            str(site_name or '').strip().lower()
            for site_name in site_names
            if str(site_name or '').strip().lower() in _PLUGIN_DEFINITIONS
        }
        with self._registry_lock:
            hosts = [self._process_hosts[slug] for slug in sorted(normalized_sites) if slug in self._process_hosts]
        for host in hosts:
            host.restart()

    def list_plugins(self) -> list[dict[str, Any]]:
        items = []
        for site_name in _PLUGIN_DEFINITIONS:
            plugin = self._load_plugin(site_name)
            manifest = plugin.manifest()
            items.append(
                {
                    'plugin_id': manifest.runtime_id,
                    'display_name': manifest.display_name or manifest.runtime_id,
                    'description': manifest.description,
                    'version': manifest.version,
                    'enabled': True,
                    'capabilities': [item.to_dict() for item in manifest.capabilities],
                    'sites': [item.to_dict() for item in manifest.sites],
                }
            )
        return items

    def build_site_catalog(self) -> dict[str, dict]:
        catalog: dict[str, dict] = {}
        for site_name in _PLUGIN_DEFINITIONS:
            manifest = self._load_plugin(site_name).manifest()
            for site in manifest.sites:
                slug = site.site_name.strip().lower()
                defaults = dict(site.metadata or {})
                item = catalog.setdefault(
                    slug,
                    {
                        'label': defaults.get('label') or site.site_name,
                        'domains': [],
                        'aliases': [],
                        'enabled': True,
                        'features': [],
                    },
                )
                item['label'] = defaults.get('label') or item.get('label') or site.site_name
                if site.test_url:
                    item['test_url'] = site.test_url
                for alias in [str(alias).strip().lower() for alias in defaults.get('aliases') or [] if alias]:
                    if alias not in item['aliases']:
                        item['aliases'].append(alias)
                for key in ('http', 'proxy', 'login', 'rate_limit', 'cookie', 'metadata', 'icon_url'):
                    value = defaults.get(key)
                    if value is not None:
                        item[key] = value
                for feature in site.features:
                    if feature not in item['features']:
                        item['features'].append(feature)
                for domain in site.domains:
                    normalized = str(domain).strip().lower()
                    if normalized and normalized not in item['domains']:
                        item['domains'].append(normalized)
        return catalog

    def get_supported_sites(self, capability: str) -> set[str]:
        return {
            site.site_name
            for site_name in _PLUGIN_DEFINITIONS
            for site in self._load_plugin(site_name).manifest().sites
            if capability in set(site.features)
        }

    def has_capability(self, site_name: str, capability: str) -> bool:
        slug = site_name.strip().lower()
        if slug not in _PLUGIN_DEFINITIONS:
            return False
        return slug in self.get_supported_sites(capability)

    def find_site_by_domain(self, domain: str | None) -> str | None:
        if not domain:
            return None
        value = domain.split(':')[0].strip().lower()
        for slug, info in self.build_site_catalog().items():
            for configured_domain in info.get('domains') or []:
                configured = str(configured_domain).strip().lower()
                if value == configured or value.endswith(f'.{configured}'):
                    return slug
        return None

    def invoke(
        self,
        capability: str,
        payload: dict[str, Any] | None = None,
        *,
        site_name: str | None = None,
        domain: str | None = None,
    ) -> SitePluginResult:
        slug = site_name.strip().lower() if site_name else self.find_site_by_domain(domain)
        if not slug or not self.has_capability(slug, capability):
            raise ValueError(
                f'No plugin capability route found: capability={capability}, site={site_name}, domain={domain}'
            )

        manifest = self._load_plugin(slug).manifest()
        capability_manifest = next((item for item in manifest.capabilities if item.name == capability), None)
        timeout_ms = int(getattr(capability_manifest, 'timeout_ms', None) or 30000)
        host = self._get_process_host(slug, manifest)
        response = host.invoke(capability, dict(payload or {}), timeout_ms / 1000)
        error = response.get('error')
        error_details = error.get('details') if isinstance(error, dict) else None
        if error_details is not None and not isinstance(error_details, dict):
            error_details = {'raw_details': str(error_details)}
        if isinstance(error, dict):
            error_details = dict(error_details or {})
            error_code = _stringify_error_code(error.get('code'))
            if error_code is not None:
                error_details.setdefault('code', error_code)
            if error.get('retry_after_seconds') is not None:
                error_details.setdefault('retry_after_seconds', error.get('retry_after_seconds'))
        else:
            error_code = None
        plugin_error = None
        if isinstance(error, dict):
            plugin_error = SitePluginError(
                message=str(error.get('message') or 'Site plugin failed'),
                details=dict(error_details or {}),
                retryable=bool(error.get('retryable', False)),
                code=error_code,
            )
        elif error is not None:
            plugin_error = SitePluginError(message=str(error), details={})
        return SitePluginResult(
            ok=bool(response.get('ok')),
            data=response.get('data'),
            error=plugin_error,
            retryable=bool(response.get('retryable', False)),
        )

    def _get_process_host(self, slug: str, manifest) -> _PluginProcessHost:
        with self._registry_lock:
            host = self._process_hosts.get(slug)
            if host is not None:
                return host
            health_policy = getattr(manifest, 'health_policy', None)
            if isinstance(health_policy, dict):
                startup_timeout_ms = health_policy.get('startup_timeout_ms')
            else:
                startup_timeout_ms = getattr(health_policy, 'startup_timeout_ms', None)
            host = _PluginProcessHost(
                self._repo_root,
                slug,
                startup_timeout_seconds=int(startup_timeout_ms or 30000) / 1000,
            )
            self._process_hosts[slug] = host
            return host


_site_plugin_registry = SitePluginRegistry()


def get_site_plugin_registry() -> SitePluginRegistry:
    return _site_plugin_registry

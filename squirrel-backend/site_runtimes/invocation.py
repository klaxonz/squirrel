from __future__ import annotations

import json
import logging
import time
import urllib.error
from collections.abc import Callable

from crawl import SiteRuntimeError, SiteRuntimeInvokeRequest, SiteRuntimeInvokeResponse

from .audit import SiteRuntimeAuditWriter
from .health import SiteRuntimeHealthChecker, to_health_snapshot
from .models import SiteRuntimeHandle, SiteRuntimeRecord, SiteRuntimeState, SiteRuntimeTarget
from .transport import SiteRuntimeTransportClient

logger = logging.getLogger(__name__)


def build_invoke_details(
    target: SiteRuntimeTarget,
    request: SiteRuntimeInvokeRequest,
    handle: SiteRuntimeHandle,
    *,
    elapsed_ms: int | None = None,
    reason: str | None = None,
) -> dict:
    payload = dict(request.payload or {})
    details = {
        'request_id': request.request_id,
        'task_id': payload.get('task_id'),
        'runtime_id': target.runtime_id,
        'version': target.version,
        'capability': target.capability,
        'site_name': request.site_name or target.site_name,
        'domain': target.domain or request.metadata.get('domain'),
        'url': payload.get('url'),
        'timeout_ms': request.timeout_ms,
        'endpoint': handle.endpoint,
        'process_id': handle.process_id,
    }
    if elapsed_ms is not None:
        details['elapsed_ms'] = elapsed_ms
    if reason is not None:
        details['reason'] = reason
    return details


def format_invoke_timeout_message(details: dict) -> str:
    return (
        'Site runtime request timed out: '
        f"runtime_id={details.get('runtime_id')}, "
        f"version={details.get('version')}, "
        f"capability={details.get('capability')}, "
        f"request_id={details.get('request_id')}, "
        f"task_id={details.get('task_id')}, "
        f"site_name={details.get('site_name')}, "
        f"domain={details.get('domain')}, "
        f"url={details.get('url')}, "
        f"timeout_ms={details.get('timeout_ms')}, "
        f"elapsed_ms={details.get('elapsed_ms')}, "
        f"endpoint={details.get('endpoint')}, "
        f"process_id={details.get('process_id')}"
    )


class SiteRuntimeInvocationClient:
    def __init__(
        self,
        transport_client: SiteRuntimeTransportClient,
        health_checker: SiteRuntimeHealthChecker,
        audit_writer: SiteRuntimeAuditWriter,
        mark_failed: Callable[[str, str, str], SiteRuntimeHandle | None],
    ) -> None:
        self._transport_client = transport_client
        self._health_checker = health_checker
        self._audit_writer = audit_writer
        self._mark_failed = mark_failed

    def invoke(
        self,
        target: SiteRuntimeTarget,
        request: SiteRuntimeInvokeRequest,
        handle: SiteRuntimeHandle,
        record: SiteRuntimeRecord | None,
    ) -> SiteRuntimeInvokeResponse:
        outbound_request = self._build_outbound_request(request)
        started_at = time.monotonic()
        if record is not None:
            self._audit_writer.append_event(
                record,
                event='invoke_started',
                details=build_invoke_details(target, request, handle),
            )

        try:
            raw_response = self._transport_client.request_json(
                handle.endpoint,
                '/invoke',
                payload={'request': outbound_request.to_dict()},
                timeout=max((request.timeout_ms or 5000) / 1000, 1.0),
            )
            response = SiteRuntimeInvokeResponse.from_dict(raw_response)
            self._refresh_health(target, handle)
            self._append_completed_event(target, request, handle, record, started_at, response)
            return response
        except TimeoutError as exc:
            return self._build_failed_response(
                target,
                request,
                handle,
                record,
                started_at,
                exc,
                SiteRuntimeError.timeout,
                format_invoke_timeout_message,
                retryable=True,
            )
        except urllib.error.URLError as exc:
            return self._build_failed_response(
                target,
                request,
                handle,
                record,
                started_at,
                exc,
                SiteRuntimeError.network_error,
                lambda _details: 'Site runtime request failed',
            )
        except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
            return self._build_failed_response(
                target,
                request,
                handle,
                record,
                started_at,
                exc,
                SiteRuntimeError.bad_response,
                lambda _details: 'Site runtime returned an invalid response object',
            )

    @staticmethod
    def _build_outbound_request(request: SiteRuntimeInvokeRequest) -> SiteRuntimeInvokeRequest:
        payload = dict(request.payload)
        payload.setdefault('request_id', request.request_id)
        payload.setdefault('site_name', request.site_name)
        payload.setdefault('timeout_ms', request.timeout_ms)
        payload.setdefault('metadata', dict(request.metadata))

        return SiteRuntimeInvokeRequest(
            request_id=request.request_id,
            capability=request.capability,
            payload=payload,
            site_name=request.site_name,
            timeout_ms=request.timeout_ms,
            metadata=dict(request.metadata),
            trace_id=request.trace_id,
        )

    def _refresh_health(self, target: SiteRuntimeTarget, handle: SiteRuntimeHandle) -> None:
        if not handle.endpoint:
            return
        try:
            health = self._health_checker.fetch_health(handle.endpoint, timeout=1.0)
            handle.health = to_health_snapshot(target.runtime_id, health)
            handle.state = SiteRuntimeState.RUNNING if health.healthy else SiteRuntimeState.FAILED
        except (TimeoutError, urllib.error.URLError, json.JSONDecodeError) as exc:
            logger.warning(
                'Site runtime health refresh failed after invoke: runtime_id=%s, version=%s, error=%s',
                target.runtime_id,
                target.version,
                exc,
            )

    def _append_completed_event(
        self,
        target: SiteRuntimeTarget,
        request: SiteRuntimeInvokeRequest,
        handle: SiteRuntimeHandle,
        record: SiteRuntimeRecord | None,
        started_at: float,
        response: SiteRuntimeInvokeResponse,
    ) -> None:
        if record is None:
            return
        elapsed_ms = int((time.monotonic() - started_at) * 1000)
        self._audit_writer.append_event(
            record,
            event='invoke_completed',
            details={
                **build_invoke_details(target, request, handle, elapsed_ms=elapsed_ms),
                'ok': response.ok,
                'error_code': response.error.code if response.error else None,
            },
        )

    def _build_failed_response(
        self,
        target: SiteRuntimeTarget,
        request: SiteRuntimeInvokeRequest,
        handle: SiteRuntimeHandle,
        record: SiteRuntimeRecord | None,
        started_at: float,
        exc: Exception,
        error_factory,
        message_factory,
        *,
        retryable: bool = False,
    ) -> SiteRuntimeInvokeResponse:
        self._mark_failed(target.runtime_id, target.version, str(exc))
        details = build_invoke_details(
            target,
            request,
            handle,
            elapsed_ms=int((time.monotonic() - started_at) * 1000),
            reason=str(exc),
        )
        if record is not None:
            self._audit_writer.append_event(
                record,
                event='invoke_failed',
                details=details,
            )
        return SiteRuntimeInvokeResponse(
            request_id=request.request_id,
            ok=False,
            error=error_factory(
                message_factory(details),
                details=details,
            ),
            retryable=retryable,
        )

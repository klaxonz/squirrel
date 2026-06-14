from __future__ import annotations

import argparse
import importlib
import json
import logging
import os
import sys

from crawl import SiteRuntime

from infrastructure.site_runtimes.bridge_runtime_state import configure_backend_runtime_state
from infrastructure.site_runtimes.bridge_server import BridgeHandler, BridgeServer

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Squirrel site runtime bridge")
    parser.add_argument("--entrypoint", required=True)
    parser.add_argument("--runtime-id", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--data-dir")
    parser.add_argument("--granted-permission", action="append", default=[])
    parser.add_argument("--network-policy")
    parser.add_argument("--max-runtime-seconds", type=float)
    parser.add_argument("--import-path", action="append", default=[])
    parser.add_argument("--trace-id")
    return parser.parse_args()


def _load_runtime(entrypoint: str) -> SiteRuntime:
    module_name, _, factory_name = entrypoint.partition(":")
    if not module_name or not factory_name:
        raise RuntimeError(f"Invalid runtime entrypoint: {entrypoint}")

    importlib.invalidate_caches()
    module = importlib.import_module(module_name)
    factory = getattr(module, factory_name, None)
    if factory is None:
        raise RuntimeError(f"Runtime factory not found: {entrypoint}")

    runtime = factory()
    if not isinstance(runtime, SiteRuntime):
        raise RuntimeError(f"Runtime factory did not return SiteRuntime: {entrypoint}")
    return runtime


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        force=True,
    )
    args = _parse_args()

    trace_id = args.trace_id or os.environ.get("SQUIRREL_TRACE_ID")
    if trace_id:
        from shared_kernel.infrastructure.trace import set_trace_id
        set_trace_id(trace_id)

    for import_path in args.import_path:
        if import_path and import_path not in sys.path:
            sys.path.insert(0, import_path)

    runtime = _load_runtime(args.entrypoint)
    site_configs = json.loads(os.environ.get("SQUIRREL_SITE_RUNTIME_SITE_CONFIGS") or "{}")
    configure_backend_runtime_state(site_configs)
    runtime.start({
        "runtime_id": args.runtime_id,
        "version": args.version,
        "data_dir": args.data_dir,
        "granted_permissions": list(args.granted_permission or []),
        "network_policy": json.loads(args.network_policy) if args.network_policy else None,
        "runtime_policy": {
            "max_runtime_seconds": args.max_runtime_seconds,
        },
    })

    server = BridgeServer((args.host, args.port), BridgeHandler)
    server.runtime = runtime

    try:
        server.serve_forever()
    finally:
        try:
            runtime.stop()
        except Exception:
            # cleanup during shutdown -- must not propagate
            pass
        server.server_close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

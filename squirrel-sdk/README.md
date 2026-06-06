# Squirrel SDK

The SDK is the plugin-facing API for Squirrel Runtime V2 packages.

## Supported path

New plugins should:

- declare a manifest with explicit capabilities
- expose `create_site_runtime()`
- let the backend discover them from `site-runtime.json`

Legacy in-process registries and helper decorators have been removed.

## Installation

```bash
pip install squirrel-sdk
```

## Runtime V2 quick start

```python
from crawl import (
    SiteRuntimeCapability,
    SiteRuntimeManifest,
    SiteRuntimePermission,
    SiteRuntimeSite,
    create_site_runtime,
)


def _extract_video(payload):
    return {
        'success': True,
        'data': {
            'title': 'Example Video',
            'url': payload['url'],
            'thumbnail': 'https://example.com/thumb.jpg',
            'duration': 120,
            'publish_date': None,
            'extra_data': {'site': 'example'},
        },
    }


def get_site_runtime():
    manifest = SiteRuntimeManifest(
        runtime_id='example',
        version='0.1.0',
        display_name='Example',
        description='Example Runtime V2 plugin',
        capabilities=[
            SiteRuntimeCapability(
                name='extract_video',
                description='Extract metadata for an example video URL.',
                response_schema={'type': 'object'},
                timeout_ms=30000,
            ),
        ],
        sites=[
            SiteRuntimeSite(
                site_name='example',
                domains=['example.com', 'www.example.com'],
                test_url='https://www.example.com',
                features=['extract_video'],
            ),
        ],
        permissions=[
            SiteRuntimePermission(
                name='network:http',
                description='Access example.com over HTTP.',
                required=True,
            ),
        ],
    )
    return create_site_runtime(
        manifest=manifest,
        capability_handlers={'extract_video': _extract_video},
    )
```

## Primary APIs

- `SiteRuntimeManifest`, `SiteRuntimeCapability`, `SiteRuntimeSite`, `SiteRuntimePermission`
- `SiteRuntimeInvokeRequest`, `SiteRuntimeInvokeResponse`, `SiteRuntimeHealthStatus`
- `SiteRuntime`, `SiteRuntimeFactory`
- `create_site_runtime()`

`VideoMeta`, `ExtractionTask`, and `ExtractionResult` remain available for plugin
logic and payload shaping inside handlers.

The SDK remains the plugin-facing contract and helper package. Backend runtime
bootstrap state such as host-owned cookie resolution, site config projection,
and Cloudflare bypass client injection should be owned by `squirrel-backend`
instead of mutating SDK-global state.

## Removed legacy APIs

The SDK no longer exposes the old in-process plugin registration helpers or the
legacy downloader registry. Runtime V2 plugins must declare capabilities in the
manifest and expose `create_site_runtime()`.

## Requirements

- Python 3.10+
- standard library only for core runtime models
- `requests` only when using the HTTP helper modules

## License

MIT License

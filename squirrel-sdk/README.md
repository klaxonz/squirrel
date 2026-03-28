# Squirrel SDK

The SDK is the plugin-facing API for Squirrel Runtime V2 packages.

## Supported path

New plugins should:

- declare a manifest with explicit capabilities
- expose `create_plugin_runtime()`
- let the backend discover them from `plugin-runtime.json`

Legacy in-process registries still exist only for compatibility with older code.

## Installation

```bash
pip install squirrel-sdk
```

## Runtime V2 quick start

```python
from crawl import (
    PluginCapability,
    PluginManifest,
    PluginPermission,
    PluginSiteManifest,
    create_plugin_runtime,
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


def get_plugin_runtime():
    manifest = PluginManifest(
        plugin_id='example',
        version='0.1.0',
        display_name='Example',
        description='Example Runtime V2 plugin',
        capabilities=[
            PluginCapability(
                name='extract_video',
                description='Extract metadata for an example video URL.',
                response_schema={'type': 'object'},
                timeout_ms=30000,
            ),
        ],
        sites=[
            PluginSiteManifest(
                site_name='example',
                domains=['example.com', 'www.example.com'],
                test_url='https://www.example.com',
                features=['extract_video'],
            ),
        ],
        permissions=[
            PluginPermission(
                name='network:http',
                description='Access example.com over HTTP.',
                required=True,
            ),
        ],
    )
    return create_plugin_runtime(
        manifest=manifest,
        capability_handlers={'extract_video': _extract_video},
    )
```

## Primary APIs

- `PluginManifest`, `PluginCapability`, `PluginSiteManifest`, `PluginPermission`
- `PluginInvokeRequest`, `PluginInvokeResponse`, `PluginHealthStatus`
- `PluginRuntime`, `PluginRuntimeFactory`
- `create_plugin_runtime()`

`VideoMeta`, `ExtractionTask`, and `ExtractionResult` remain available for plugin
logic and payload shaping inside handlers.

## Removed legacy APIs

The SDK no longer exposes the old in-process plugin registration helpers or the
legacy downloader registry. Runtime V2 plugins must declare capabilities in the
manifest and expose `create_plugin_runtime()`.

## Requirements

- Python 3.10+
- standard library only for core runtime models
- `requests` only when using the HTTP helper modules

## License

MIT License

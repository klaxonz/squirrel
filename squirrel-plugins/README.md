Squirrel Plugins
================

This repository hosts site crawling plugins that depend on `squirrel-sdk`.

Runtime V2 package shape
------------------------

Each site folder is a standalone Python package. New plugins should target runtime V2
instead of host-side registry decorators or backend-local compatibility packages.

Minimal structure:

```
my-site/
  pyproject.toml
  plugin-runtime.json
  src/
    my_site/
      __init__.py
      runtime.py
      extractor.py
      subscription.py
```

`__init__.py` should stay minimal and export runtime metadata plus
`get_plugin_runtime`. Avoid import side effects or host-side registration hooks.

Entrypoint
----------

Expose a runtime factory entrypoint from `pyproject.toml`:

```toml
[project.entry-points."squirrel.plugins"]
my_site = "my_site.runtime:get_plugin_runtime"
```

The runtime factory should return `create_plugin_runtime(...)` and declare all
capabilities in the manifest explicitly.

Uploaded runtime V2 plugins are installed into a dedicated virtual environment
by the backend together with the `squirrel-plugin-runner` bridge package. During
workspace development, the backend can still load sibling plugin folders directly.
Runtime processes can read contextual values from `SQUIRREL_PLUGIN_*`
environment variables, including the granted permission list and plugin data
directory.

Optional manifest metadata keys:

- `metadata.runtime_policy`
- `metadata.network_policy`

These values are passed into the isolated runtime context and can be enforced by
the host runner.

Runtime metadata
----------------

Ship a `plugin-runtime.json` file next to the package root:

```json
{
  "entrypoint": "my_site.runtime:get_plugin_runtime",
  "manifest": {
    "plugin_id": "my_site",
    "version": "0.1.0",
    "capabilities": [],
    "sites": [],
    "permissions": []
  }
}
```

Recommended capabilities
------------------------

Depending on the site, implement one or more of these runtime V2 capability handlers:

- `extract_video`
- `resolve_playback`
- `sync_subscription`
- `import_subscriptions`
- `resolve_subscription`
- `check_login_status`
- `fetch_subtitles`
- `build_mpd`
- `resolve_proxy_config`
- `rewrite_proxy_playlist`

Legacy in-process registration helpers have been removed from the SDK export
surface. Runtime V2 packages should instantiate their components directly inside
`runtime.py` handlers instead of relying on host-side registries.



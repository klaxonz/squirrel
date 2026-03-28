Squirrel Plugins
================

This repository hosts site crawling plugins that depend on `squirrel-sdk`.

Runtime V2 package shape
------------------------

Each site folder is a standalone Python package. New plugins should target runtime V2
instead of host-side registry decorators.

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

Legacy registry decorators such as `register_extractor()` and `register_subscription()`
still exist only for compatibility with older plugin modules. Do not use them for new
plugins unless you are intentionally maintaining a legacy in-process path.



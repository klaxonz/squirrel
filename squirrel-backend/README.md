Plugins and SDK
===============

The backend discovers crawl plugins via Python entry points. Install packages
that expose the `squirrel.crawl.plugins` group. The `squirrel-sdk` provides
the plugin-facing API and registries used by both backend and plugins.

Plugins are mandatory – legacy `sites/` are no longer bridged. Ensure the
corresponding plugins are installed for the domains you need.

Install dependencies
--------------------

### 1. Install Python dependencies

```bash
# Install all dependencies from Pipfile
pipenv install

# Install squirrel-sdk in editable mode (for development)
pipenv run pip install -e ../squirrel-sdk
```

**Note**: `squirrel-sdk` is installed separately because it's a local dependency 
not available on PyPI. The `-e` flag enables editable mode, so changes to the SDK 
will be reflected immediately without reinstalling.

### 2. Install plugin packages

```bash
# Install from plugin packages (if built)
pipenv run pip install ../plugin_packages/bilibili_plugin.zip
pipenv run pip install ../plugin_packages/youtube_plugin.zip
# ... other plugins
```

### For Production/Docker

In production environments, install the SDK directly from the local path:

```bash
pip install /path/to/squirrel-sdk
```




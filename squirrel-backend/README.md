Plugins and SDK
===============

The backend discovers crawl plugins via Python entry points. Install packages
that expose the `squirrel.crawl.plugins` group. The `squirrel-sdk` provides
the plugin-facing API and registries used by both backend and plugins.

Plugins are mandatory – legacy `sites/` are no longer bridged. Ensure the
corresponding plugins are installed for the domains you need.

Install dependencies
--------------------

- Ensure `squirrel-sdk` is installed in the backend environment (see Pipfile entry).
- Install plugin packages, e.g. `pip install squirrel-plugin-bilibili`.




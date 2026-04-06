# Plugin Runtime Storage Refactor Design

**Goal:** Separate declarative configuration from mutable plugin runtime state, remove path coupling inside the plugin subsystem, and make plugin storage layout explicit, migratable, and maintainable.

**Scope:** `squirrel-backend/plugins` and related tests. No frontend API shape changes. No plugin protocol changes.

## Problem

The current plugin runtime storage design mixes multiple concerns:

- Human-managed configuration and mutable runtime data both live under `config/`
- The storage root name `plugin_runtime_v2` leaks migration history into long-term runtime structure
- `PluginManager` infers workspace paths through `PluginInstaller` internals
- `PluginInstallStore` leaves behind many `installations.*.tmp` files when writes fail or are interrupted
- The runtime layout is implicit across multiple modules instead of being a shared contract

## Design

### Storage boundaries

The repository should use these storage categories:

- `config/`
  - Human-managed declarative configuration only
  - Examples: `sites.json`, `site_cookies/`
- `data/plugins/state/`
  - Host-managed persistent plugin state
  - `installations.json`
- `data/plugins/artifacts/`
  - Uploaded packages and extracted install directories
  - `packages/`, `installs/`
- `data/plugins/runtime/`
  - Per-plugin isolated runtime environments
- `data/plugins/data/`
  - Per-plugin mutable data owned by installed plugins

### Shared path contract

Add a new backend module, `plugins.paths`, that defines a single `PluginPaths` contract.

It should expose:

- `repo_root`
- `workspace_plugins_dir`
- `state_dir`
- `artifacts_dir`
- `packages_dir`
- `installs_dir`
- `runtime_dir`
- `plugin_data_dir`
- `installations_file`
- `legacy_root`

All plugin storage consumers must use `PluginPaths`. No module should construct storage paths ad hoc or reach into another module's private path fields.

### Migration model

At startup, plugin storage should support one legacy source:

- `config/plugin_runtime_v2`

Migration behavior:

1. If the new layout already contains `installations.json`, use it and skip migration.
2. If the new layout is empty and the legacy directory exists, migrate once.
3. Migrate:
   - `installations.json`
   - `packages/`
   - `installs/`
   - `runtime/`
   - `data/`
4. Remove orphaned legacy `installations.*.tmp` files during migration.
5. After migration, only the new layout is authoritative.

No long-term dual-read or dual-write behavior should remain.

### Store behavior

`PluginInstallStore` remains JSON-backed but should be tightened:

- Use `PluginPaths.installations_file`
- Clean orphaned temp files on startup
- Use atomic write with explicit cleanup on failure
- Keep current JSON schema to avoid unnecessary data migration complexity

Optional file locking can be deferred if not required for current single-node behavior.

### Installer behavior

`PluginInstaller` should consume `PluginPaths` and use:

- `packages_dir`
- `installs_dir`
- `runtime_dir`
- `plugin_data_dir`

The installer should not expose its internal root for discovery logic.

### Manager behavior

`PluginManager` should:

- Receive `PluginPaths`
- Run legacy migration during initialization
- Discover workspace plugins from `workspace_plugins_dir`
- Stop inferring paths from `PluginInstaller` internals

### Backward compatibility

Preserve:

- Existing `PluginInstallRecord` fields
- Existing workspace plugin discovery semantics
- Existing plugin API behavior

Only local storage layout changes.

## Error handling

- Migration must be fail-fast. Partial migration should not silently continue.
- Temp-file cleanup failures should be logged and tolerated when safe.
- Invalid workspace plugin metadata should continue to be skipped without taking down the host.

## Testing

Add or update tests for:

- New path layout generation
- Legacy `config/plugin_runtime_v2` migration
- No migration when new state already exists
- Temp-file cleanup in `PluginInstallStore`
- Workspace discovery using shared paths instead of installer internals

## Non-goals

- Moving plugin state into the database
- Changing plugin manifests or runtime protocol
- Frontend changes
- Cross-node plugin storage coordination


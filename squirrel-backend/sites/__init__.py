"""In-tree site packages.

First-party site integrations live here as plain modules:

- ``crawl`` — shared crawl interface layer (protocols, http, exceptions,
  importer/extractor/subscription bases, config getters).
- ``squirrel_youtube`` / ``squirrel_bilibili`` — per-site implementations.

The directory is added to ``sys.path`` (see ``sitecustomize.py`` and the
entry points) so the historical top-level import names (``crawl``,
``squirrel_youtube``, ``squirrel_bilibili``) keep resolving unchanged.
"""

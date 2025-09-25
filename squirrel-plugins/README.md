Squirrel Plugins
================

This repository hosts site crawling plugins that depend on `squirrel-sdk`.

Packaging
---------

Each subfolder is a standalone Python package. Example structure for a site:

```
my-site/
  pyproject.toml
  src/
    my_site/
      __init__.py
      subscription.py
      extractor.py
```

Expose plugin modules via entry points so the backend can auto-discover them:

```
[project.entry-points]
"squirrel.crawl.plugins" = { my_site = "my_site" }
```

Use the SDK to register your classes:

```python
from crawl import register_subscription, BaseExtractor

@register_subscription("youtube", ["youtube.com", "youtu.be"])
class YoutubeSubscription:
    ...
```



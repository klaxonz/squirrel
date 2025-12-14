# Squirrel SDK v2.0

Squirrel plugin SDK - Provides stable plugin interfaces for the Squirrel media subscription platform.

## Introduction

Squirrel SDK v2.0 provides a standardized interface for developing video content crawling and processing plugins. This SDK uses modern Python design patterns with Protocol-based interfaces supporting structural type checking.

## Key Features

- **Protocol Interfaces**: Uses Python Protocol to define interfaces with structural type checking
- **Unified Data Model**: VideoMeta as the only data model, simplifying serialization/deserialization
- **Unified Registry System**: All plugins use a unified registration mechanism
- **Type Safety**: Complete type annotation support
- **Auto Registration**: Automatic plugin class registration
- **Lightweight**: Core interfaces only depend on Python standard library (HTTP utilities require requests)

## Quick Start

### Installation

```bash
pip install squirrel-sdk
```

### Creating a Simple Extractor Plugin

#### Method 1: Using Base Class (Recommended, Simple)

```python
from squirrel_sdk.crawl import BaseExtractor, ExtractionTask, ExtractionResult, VideoMeta

class MyExtractor(BaseExtractor):
    site_name = "example"
    supported_domains = ["example.com", "www.example.com"]
    
    def can_handle(self, url: str) -> bool:
        return any(domain in url for domain in self.supported_domains)
    
    def extract(self, task: ExtractionTask) -> ExtractionResult:
        # Implement your extraction logic
        video_meta = VideoMeta(
            title="Example Video",
            url=task.url,
            thumbnail="https://example.com/thumb.jpg",
            duration=120,
        )
        return ExtractionResult(success=True, data=video_meta)
```

#### Method 2: Using Protocol (More Flexible)

```python
from squirrel_sdk.crawl import (
    Extractor, ExtractionTask, ExtractionResult, VideoMeta,
    register_extractor
)

@register_extractor("example", ["example.com", "www.example.com"])
class MyExtractor:
    site_name = "example"
    supported_domains = ["example.com", "www.example.com"]
    
    def can_handle(self, url: str) -> bool:
        return any(domain in url for domain in self.supported_domains)
    
    def extract(self, task: ExtractionTask) -> ExtractionResult:
        video_meta = VideoMeta(
            title="Example Video",
            url=task.url,
            thumbnail="https://example.com/thumb.jpg",
            duration=120,
        )
        return ExtractionResult(success=True, data=video_meta)
    
    def validate_url(self, url: str) -> bool:
        return self.can_handle(url)
```

Plugins are automatically registered to the Squirrel system.

## Core Interfaces

### VideoMeta (Primary Data Model)

`VideoMeta` is the standard structure for video metadata and the only data model in the SDK:

- `title`: Video title (required)
- `url`: Video URL (required)  
- `thumbnail`: Thumbnail URL (optional)
- `duration`: Video duration in seconds (optional)
- `publish_date`: Publication date (optional)
- `extra_data`: Site-specific additional data (optional)

All extractors must return `VideoMeta` instances.

### ExtractionTask

Represents an extraction task containing the URL to process and related metadata.

### ExtractionResult  

The result of an extraction operation, containing success/failure status and extracted data. The `data` field must contain a `VideoMeta` instance.

### Extractor Protocol

Interfaces are defined using Protocol, supporting structural type checking:

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Extractor(Protocol):
    site_name: str
    supported_domains: List[str]
    
    def can_handle(self, url: str) -> bool: ...
    def extract(self, task: ExtractionTask) -> ExtractionResult: ...
    def validate_url(self, url: str) -> bool: ...
```

Any class implementing these methods can be used as an extractor without inheriting from a specific base class.

## Design Improvements

### v2.0 Major Improvements

1. **Protocol Interfaces**: Uses `typing.Protocol` instead of ABC, supporting structural type checking
2. **Unified Data Model**: `VideoMeta` as the only data model, simplifying serialization
3. **Unified Registry System**: All plugin types use unified `PluginRegistry`
4. **Removed Legacy Code**: Removed all old ABC interfaces and backward compatibility code

## Dependencies

- **Core Interfaces**: Only depends on Python standard library
- **HTTP Utilities**: Requires `requests` library (for `http.py` module)
- **Type Checking**: Requires Python 3.10+ for complete type annotation support

## License

MIT License

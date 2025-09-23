# Squirrel SDK

Squirrel plugin SDK - 为 Squirrel 媒体订阅平台提供稳定的插件接口。

## 简介

Squirrel SDK 提供了一套标准化的接口，用于开发视频内容爬取和处理插件。这个 SDK 设计为轻量级、无外部依赖（仅使用 Python 标准库），以确保最大的可移植性。

## 主要特性

- **轻量级设计**: 仅依赖 Python 标准库
- **简单易用**: 提供基类和装饰器简化插件开发
- **类型安全**: 完整的类型注解支持
- **自动注册**: 插件类自动注册机制

## 快速开始

### 安装

```bash
pip install squirrel-sdk
```

### 创建简单的提取器插件

```python
from squirrel_sdk.crawl import BaseExtractor, ExtractionTask, ExtractionResult, VideoMeta

class MyExtractor(BaseExtractor):
    site_name = "example"
    supported_domains = ["example.com", "www.example.com"]
    
    def can_handle(self, url: str) -> bool:
        return any(domain in url for domain in self.supported_domains)
    
    def extract(self, task: ExtractionTask) -> ExtractionResult:
        # 实现你的提取逻辑
        video_meta = VideoMeta(
            title="示例视频",
            url=task.url,
            thumbnail="https://example.com/thumb.jpg",
            duration=120,
        )
        return ExtractionResult(success=True, data=video_meta)
```

插件会自动注册到 Squirrel 系统中。

## 核心接口

### VideoMeta

视频元数据的标准结构：

- `title`: 视频标题（必填）
- `url`: 视频 URL（必填）  
- `thumbnail`: 缩略图 URL（可选）
- `duration`: 视频时长，单位秒（可选）
- `publish_date`: 发布日期（可选）
- `extra_data`: 站点特定的额外数据（可选）

### ExtractionTask

表示一个提取任务，包含要处理的 URL 和相关元数据。

### ExtractionResult  

提取操作的结果，包含成功/失败状态和提取到的数据。

## 许可证

MIT License

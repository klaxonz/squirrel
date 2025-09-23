# Squirrel Crawl SDK – Plugin Author Guide

This guide explains **what data your extractor plugin should return** so that
`squirrel-backend` can persist it to the database and继续后续下载/推送流程。

> TL;DR 只要保证 `ExtractionResult.success=True` 且 `data` 字典包含下表字段，
> 其余解析、存储、下载、订阅逻辑都会由 backend 自动完成。

插件应返回 `VideoMeta` 数据类，而不是裸字典::

    from squirrel_sdk.crawl import VideoMeta, ExtractionResult

    info = VideoMeta(
        title="Hello",
        url=task.url,
        duration=95,
        extra_data={"bvid": "BV17..."},
    )
    return ExtractionResult(success=True, data=info)

VideoMeta 字段一览：

| 字段名          | 必填 | 类型          | 说明 |
|-----------------|------|---------------|------|
| `title`         | ✔️   | `str`         | 视频标题 |
| `url`           | ✔️   | `str`         | 视频页 URL |
| `thumbnail`     |      | `str`         | 缩略图 URL |
| `duration`      |      | `int`         | 秒 |
| `publish_date`  |      | `str | int`   | 详见下方格式 |
| `extra_data`    |      | `dict | None` | 站点特有字段，直接写入 DB `extra_data` 列 |

示例：
```python
ExtractionResult(
    success=True,
    data={
        "title": "【BV17x411w7KC】Hello World",
        "url": "https://www.bilibili.com/video/BV17x411w7KC",
        "thumbnail": "https://i0.hdslb.com/bfs/...",
```

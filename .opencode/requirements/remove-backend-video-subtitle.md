---
title: 移除后端视频播放与字幕相关代码
status: done
created: 2026-06-07
---

# 需求：移除后端视频播放与字幕相关代码

## 背景
视频播放和字幕功能已全部迁移到桌面端（Electron）实现，后端不再需要承担视频流代理和字幕获取的职责。需要清理后端中这些已不再使用的代码，减少维护负担。

## 目标
移除 squirrel-backend 中与视频播放、字幕相关的路由、服务、模型、核心模块，保持代码整洁。

## 功能描述
- 移除视频流代理模块（`core/streaming/`）
- 移除字幕服务（`services/video_subtitle_service.py`）
- 移除视频播放相关路由（proxy、subtitles 端点）
- 清理关联的 schema、测试文件

## 验收标准
- [ ] 视频代理模块（`core/streaming/`）已删除
- [ ] 字幕服务已删除
- [ ] 视频路由中的 proxy 和 subtitles 端点已移除
- [ ] 关联的 schema、测试、import 已清理
- [ ] 后端 lint 和测试通过

## 关联

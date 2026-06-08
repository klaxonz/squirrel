---
title: 移除后端视频播放与字幕相关代码
status: implemented
created: 2026-06-07
requirements: .opencode/requirements/remove-backend-video-subtitle.md
---

# 设计方案：移除后端视频播放与字幕相关代码

## 关联需求
- `.opencode/requirements/remove-backend-video-subtitle.md`

## 涉及文件

### 删除文件（9 个）
| 文件 | 说明 |
|------|------|
| `core/streaming/proxy.py` | 视频流代理核心（VideoProxy, ConnectionManager, HttpRequester 等） |
| `core/streaming/__init__.py` | streaming 模块导出 |
| `core/exceptions/proxy_exceptions.py` | 代理异常类（ProxyException 等） |
| `schemas/proxy.py` | VideoProxyRequest / ProxyErrorResponse schema |
| `services/video_subtitle_service.py` | 字幕服务（fetch_video_subtitles） |
| `tests/core/test_streaming_proxy.py` | 代理相关测试（1090 行） |
| `tests/routes/test_video_runtime_routes.py` | 字幕路由测试（4 个测试） |

### 修改文件（2 个）
| 文件 | 改动 |
|------|------|
| `routes/video.py` | 移除 proxy 和 subtitles 两个 endpoint 及对应 import |
| `routes/middleware/auth.py` | 移除 PUBLIC_PATH_PREFIXES 中的 `/api/video/proxy` |

### 不受影响（保留）
- `routes/video.py` 中保留：list / detail / random / remote-save
- `routes/video_history.py` / `video_interaction.py` / `video_clip_marker.py`
- 所有视频 model（Video, VideoHistory 等）
- 视频 listing / CRUD / extraction 服务
- 缩略图挂载（`/api/video/thumbnail` public path 保留）

## 改动思路

1. **删除** `core/streaming/` 目录（streaming 模块仅含 proxy 相关代码）
2. **删除** `core/exceptions/proxy_exceptions.py`（仅被 proxy.py 引用）
3. **删除** `schemas/proxy.py`（仅被 proxy endpoints 引用）
4. **删除** `services/video_subtitle_service.py`
5. **修改** `routes/video.py`：移除 proxy 和 subtitles endpoint，移除对应 import
6. **修改** `routes/middleware/auth.py`：移除 `/api/video/proxy` 公开路径
7. **删除** 对应测试文件

## 验收标准
- [x] `core/streaming/` 目录已删除
- [x] `core/exceptions/proxy_exceptions.py` 已删除
- [x] `schemas/proxy.py` 已删除
- [x] `services/video_subtitle_service.py` 已删除
- [x] `routes/video.py` 中 proxy 和 subtitles endpoint 已移除
- [x] `routes/middleware/auth.py` 中 `/api/video/proxy` 已移除
- [x] 对应测试文件已删除或更新
- [x] lint 和测试通过

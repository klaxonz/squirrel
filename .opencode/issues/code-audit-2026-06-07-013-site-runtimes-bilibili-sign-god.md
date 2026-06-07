---
title: 'Site-runtimes: bilibili sign.py 上帝模块 (536行)'
severity: high
category: code-smell
location: squirrel-site-runtimes/bilibili/src/squirrel_bilibili/sign.py
---

## 问题描述

`sign.py` 处理 6+ 种不相关的责任：
1. WBI 签名算法 + key 缓存
2. HTTP 请求辅助（_send_request, _get_json）
3. 视频 ID 解析与 URL 规范化/重定向
4. 视频信息获取和播放数据获取
5. 订阅目标解析（5 种资源类型）
6. 用户卡片/频道/系列 API 调用
7. 收藏夹 API 调用
8. 导航/关注 API 调用

合计 20+ 函数。

## 影响

- 修改一个 API endpoint 可能影响不相关功能
- 无法单独测试某一类 API 逻辑
- 新开发者难以理解职责边界

## 建议方向

拆分为：
- `sign.py` — 仅 WBI 签名算法
- `api_client.py` — 共享 HTTP helper（_send_request, _get_json）
- `video_api.py` — 视频信息 + 播放数据 + 基础信息构建
- `subscription_api.py` — 订阅目标解析 + 相关 API

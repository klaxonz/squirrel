---
title: VideoService/SubscriptionService 空壳门面类仅做 *args,**kwargs 透传
status: open
severity: medium
category: architecture
location: squirrel-backend/services/video_service.py:28, services/subscription_service.py
---

## 问题描述

`VideoService` 和 `SubscriptionService` 两个类的所有方法都是 `@staticmethod`，体内部仅执行 `*args, **kwargs` 透传到已直接导入的模块级函数。例如 `VideoService.get_video()` 仅调用 `get_video()`（已定义在 `video_list_service.py`）。

路由中通过 `Depends(get_video_service)` 获取实例，但 `get_video_service()` 每次返回新对象（无状态）。这些类未提供任何接口抽象、多态能力或 DI 容器集成。

## 影响

- 额外间接层无任何收益，仅增加理解成本
- 每个新端点需在两个位置添加方法
- 误导新开发者认为项目使用了 Service 层模式

## 建议方向

移除空壳类，让路由直接依赖模块级函数或单例服务对象。若测试替身是目标，使用 `unittest.mock.patch` 直接 mock 函数，或引入真正的 DI 框架。

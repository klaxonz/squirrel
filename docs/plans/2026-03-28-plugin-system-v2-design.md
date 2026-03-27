# 插件系统 V2 设计

## 目标

将当前“目录扫描 + import 副作用注册 + 进程内执行”的插件系统重构为一套面向不可信第三方插件的运行时架构，同时满足安装后立即生效、启用/禁用即时切换、站点能力统一建模这三个核心目标。

## 设计结论

### 1. 宿主与插件隔离

V2 不再允许插件进入宿主进程内执行。

统一改为：

- 宿主进程负责安装、发现、鉴权、进程编排、能力路由
- 每个插件运行在独立子进程
- 宿主与插件之间只通过显式 RPC 协议通信

这条是 V2 的硬约束，不保留进程内 side-effect 注册作为基础能力。

### 2. 发现机制统一

V2 使用标准 Python 插件包和 entry point 作为唯一正式发现入口。

统一规则：

- 插件必须是标准 Python 包
- 插件必须声明受控 entry point
- 宿主只发现插件包，不直接导入业务模块执行业务逻辑
- 安装后由宿主拉起插件 runtime 完成握手，再注册到宿主侧能力索引

不再以 `plugins_ext` 目录扫描和 `sys.path` 注入作为主路径。

### 3. 宿主侧统一模型

宿主侧只维护三类一等对象：

- `PluginManifest`
- `PluginRuntimeStatus`
- `CapabilityRegistration`

业务层不再直接依赖插件类、插件模块、SDK 全局 registry 实例。

### 4. 插件协议统一

每个插件 runtime 只允许暴露固定协议：

- `manifest()`
- `start(context)`
- `stop()`
- `health()`
- `invoke(capability, payload)`

插件不再通过 `register_extractor`、`register_subscription`、`BaseExtractor`、`create_plugin` 一类进程内注册机制向宿主暴露能力。

### 5. 能力模型统一

V2 不继续把宿主稳定接口建立在“extractor / handler / mpd / subtitles / proxy”这类实现层类型上。

宿主只识别统一 capability，例如：

- `extract_video`
- `resolve_playback`
- `fetch_subtitles`
- `proxy_stream`
- `sync_subscription`
- `import_subscriptions`
- `check_login_status`

插件内部可以自由拆分类与模块，但对宿主暴露的始终是统一能力协议。

### 6. 站点信息成为 manifest 一等数据

站点目录不再由多个 registry 反推。

每个插件 manifest 必须显式声明：

- `site_name`
- `domains`
- `test_url`
- `features`

宿主的站点列表、连通性入口、登录检测能力、Cookie 管理入口都以 manifest 为主来源。

### 7. 立即生效的真正含义

V2 中“立即生效”定义为：

- 安装完成后立即校验包
- 创建隔离运行环境
- 拉起新 runtime
- 握手成功后原子注册能力
- 新请求立即走新插件

不依赖主服务重启，也不依赖解释器内模块热重载。

### 8. 热更新语义改为进程切换

V2 不再支持基于 `sys.modules` 清理的模块级热重载。

统一改为：

- 停止旧 runtime
- 启动新 runtime
- 重新握手
- 重建能力快照
- 切换 active version

热更新的是 runtime 实例，而不是 Python 模块状态。

## 核心组件

### PluginManager

负责：

- discover
- install
- enable
- disable
- uninstall
- upgrade
- runtime status aggregation

### PluginInstaller

负责：

- 上传包暂存
- 包格式校验
- manifest 校验
- entry point 校验
- 校验和/签名校验
- 隔离安装目录切换

### PluginRuntimeSupervisor

负责：

- 启动插件子进程
- 心跳与存活检测
- 启动超时与请求超时
- 退出监控
- 资源限制
- drain 和优雅停止

### CapabilityRegistry

宿主侧只记录：

- 哪个插件提供哪些 capability
- 对应哪些 site/domain
- 当前健康状态与启用状态

不保存插件实现对象。

### PluginGateway

负责：

- 按 `site/domain + capability` 路由请求
- 统一请求与响应 schema
- 错误标准化
- 超时与重试边界

## 安装、升级、卸载

### 安装

标准流程：

1. 保存上传包到暂存区
2. 校验 manifest、entry point、协议版本、权限声明
3. 解压到隔离目录
4. 创建独立运行环境
5. 拉起 runtime 并握手
6. 握手成功后原子切换到 `installed + enabled`

### 升级

统一采用并行安装：

- 新版本先独立安装
- 握手与健康检查通过后切换 `active_version`
- 旧版本进入 drain
- drain 完成后停止并清理

### 卸载

统一顺序：

1. 摘除能力路由
2. 停止 runtime
3. 删除运行环境
4. 删除包与安装记录

## 安全边界

既然插件可能来自第三方，不将“ZIP 上传”视为可信边界。

V2 最低要求：

- 插件子进程独立工作目录
- 环境变量白名单
- 宿主敏感配置不直接透传
- 请求超时、启动超时、CPU/内存限制
- 受控网络权限
- 受控文件系统访问
- 响应 schema 严格校验
- 插件日志独立收集

manifest 中必须显式声明权限，例如：

- `network:http`
- `cookies:read:site/<site>`
- `storage:readwrite:plugin-data`
- `proxy:stream`
- `subscriptions:import`

授权由宿主决定，不由插件自行决定。

## 后端映射

### 替换当前插件装载链路

以下模块不再作为 V2 主路径：

- `squirrel-backend/plugins/loader.py`
- `squirrel-backend/plugins/registry.py`
- `squirrel-backend/plugins/base.py`

新增宿主核心模块：

- `squirrel-backend/plugins/manager.py`
- `squirrel-backend/plugins/supervisor.py`
- `squirrel-backend/plugins/gateway.py`
- `squirrel-backend/plugins/installer.py`
- `squirrel-backend/plugins/models.py`
- `squirrel-backend/plugins/store.py`

### 替换当前启动序列

以下入口改为依赖 `PluginManager`：

- `squirrel-backend/main.py`
- `squirrel-backend/processes/service_runtime.py`

### 替换当前业务调用路径

以下消费方逐步从 SDK registry 迁移到 `PluginGateway`：

- 登录检测：`squirrel-backend/services/site_login_status_service.py`
- 站点连通性与插件管理：`squirrel-backend/routes/plugins.py`
- 视频播放与代理：`squirrel-backend/services/video_service.py`
- 订阅导入：`squirrel-backend/services/subscription_service.py`
- 队列站点映射：`squirrel-backend/queues/queue_config.py`
- 站点目录聚合：`squirrel-backend/utils/site_catalog.py`
- 旧提取工厂：`squirrel-backend/core/extraction/factory.py`

## SDK 映射

V2 中 `squirrel-sdk` 只保留插件作者 API：

- runtime protocol
- manifest model
- capability request/response model
- error model

宿主内部 registry 和工厂逻辑迁回 backend。

也就是说：

- `register_extractor`
- `register_subscription`
- `register_user_subscription_importer`
- `register_login_checker`
- `BaseExtractor`
- `create_plugin`

都不再是 V2 主路径。

## 前端映射

插件管理页从“目录来源管理”改为“运行时与能力管理”。

建议展示：

- 名称
- 版本
- 状态
- 权限
- capability 数
- site 数
- 健康状态
- active runtime

建议操作：

- 安装
- 启用
- 禁用
- 升级
- 卸载
- 重启 runtime
- 查看日志

站点连通性和登录状态不再从旧 registry 反推，而直接来自 manifest 与 runtime 健康检查。

## 非目标

本轮不做：

- 旧插件兼容层
- 进程内 side-effect 注册兼容
- 容器级插件编排
- 多语言插件 runtime

## 风险

- 子进程运行时和宿主协议一旦设计含糊，后续 capability 会再次发散
- 站点能力如果没有统一 schema，前端和后端会继续维护多套口径
- 立即生效与不可信插件并存，意味着安装、授权、supervisor 三层必须一起落地，不能只做发现机制重构
- 升级路径如果没有 drain 机制，播放和导入长请求会出现切换抖动

## 最小验证路径

- 安装一个最小示例插件包
- 宿主完成发现、启动、握手、注册
- `/api/plugins` 能返回新 manifest/status
- `/api/plugins/sites` 能返回基于 manifest 的站点信息
- 跑通一条 `check_login_status` capability
- 跑通一条 `resolve_playback` 或 `import_subscriptions` capability
- 验证禁用、卸载、升级都能即时切换

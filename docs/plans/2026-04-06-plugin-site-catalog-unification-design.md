# 插件站点目录统一设计

## 背景

当前站点系统同时存在三份事实来源：

1. 插件 manifest 中的 `sites`
2. 后端硬编码的 `SITE_CONFIG_DEFAULTS`
3. `config/sites.json` 中保存的完整站点配置

这导致两个持续问题：

1. 新插件接入后，仍然需要手动修改后端默认配置才能完整可用。
2. 前端保存站点配置时，会把默认值和用户修改混写进 `config/sites.json`，形成新的静态快照。

结果是：

1. 插件是站点能力来源，但不是站点定义唯一来源。
2. 站点配置 UI、cookies 解析、登录检测、连通性测试对目录来源的理解不一致。
3. 新增站点时经常出现“插件已加载，但部分功能不可见或不可用”的问题。

## 目标

本次重构的目标是：

1. 插件成为站点定义唯一来源。
2. `config/sites.json` 只保存用户覆盖项，不再保存完整站点快照。
3. 后端所有读取站点配置的代码统一走一个 effective catalog 入口。
4. 新增插件站点时，不再需要手动修改后端默认配置或站点文件。
5. 明确采用 breaking change，不兼容旧 `sites.json` 结构。

## 非目标

本次不做以下事项：

1. 不兼容历史 `config/sites.json` 全量结构。
2. 不保留“无插件手工新增站点”能力。
3. 不为旧接口行为做兼容层。

## 核心设计

### 1. 站点定义来源

每个插件负责声明自己的默认站点配置。

现有 `PluginSiteManifest` 继续保留：

1. `site_name`
2. `domains`
3. `test_url`
4. `features`

新增约定：

插件在 `PluginSiteManifest.metadata` 中提供默认站点配置，包含：

1. `label`
2. `aliases`
3. `http`
4. `proxy`
5. `login`
6. `rate_limit`
7. `cookie`
8. `metadata`
9. `icon_url`，如果插件未提供静态图标路由回填时可选

这样插件 manifest 继续是唯一可分发的站点定义载体，不再依赖后端内置表。

### 2. 目录分层

新的目录模型分为三层：

1. `plugin base catalog`
   来源：已加载插件的 manifest 站点声明
2. `user override catalog`
   来源：`config/sites.json`
3. `effective catalog`
   计算方式：`plugin base catalog + user override catalog`

任何业务代码都不能直接消费前两层，只能消费 `effective catalog`。

### 3. 配置文件职责

`config/sites.json` 改为 override-only 文件。

文件格式从“完整站点定义列表”改为“按 slug 存储用户覆盖字段”，例如：

```json
{
  "youtube": {
    "enabled": true,
    "proxy": {
      "read_timeout": 240.0
    }
  },
  "youporn": {
    "http": {
      "headers": {
        "Accept-Language": "en-US,en;q=0.9"
      }
    }
  }
}
```

该文件不再要求包含：

1. `domains`
2. `label`
3. `test_url`
4. `aliases`
5. 完整 `http`、`proxy`、`login`、`rate_limit`、`metadata`

除非用户显式覆盖这些字段。

### 4. 后端统一入口

后端引入三类明确接口：

1. `build_plugin_site_catalog()`
   只从插件 manifest 聚合站点定义
2. `load_site_override_catalog()`
   只读取 `config/sites.json`
3. `get_effective_site_catalog()`
   深合并 base 和 override，作为唯一对外入口

现有模糊接口 `SiteCatalog.get_catalog()` 退役。

如果短期内不能删除，则只允许在内部过渡期调用，并最终替换为上面三个明确接口。

## API 设计

### `GET /api/sites`

保持返回 effective catalog。

用途：

1. 设置页展示
2. 前端读取站点真实配置
3. 其他业务读取统一目录

### `PUT /api/sites`

改为 override-only 接口。

请求体不再是“完整站点对象数组”，而是“override catalog”。

建议结构：

```json
{
  "sites": {
    "youtube": {
      "enabled": true
    },
    "youporn": {
      "proxy": {
        "read_timeout": 240.0
      }
    }
  }
}
```

行为：

1. 只验证允许覆盖的字段
2. 只写入 override 文件
3. 保存后立即重新计算 effective catalog
4. 返回最新 effective catalog

### 允许覆盖的字段

`PUT /api/sites` 只允许提交以下字段：

1. `enabled`
2. `aliases`
3. `http`
4. `proxy`
5. `login`
6. `rate_limit`
7. `metadata`
8. `cookie`
9. `test_url`
10. `icon_url`
11. `label`

其中：

1. `site slug` 必须已经存在于 plugin base catalog 中
2. 不允许通过配置文件新增一个插件未知站点
3. `domains` 默认不允许覆盖，避免 cookies、站点匹配和插件定义继续分裂

## 前端调整

前端设置页改为两段式数据流：

1. 初始化时读取 `GET /api/sites` 的 effective catalog
2. 保存时只提交用户修改过的 override 字段

这要求前端状态层显式区分：

1. `base/effective snapshot`
2. `dirty overrides`

不再将后端返回的完整 effective catalog 原样回写。

## 关键实现变化

### 删除硬编码默认值

删除 [site_config_defaults.py](D:/Code/init/squirrel/squirrel-backend/core/site_config_defaults.py) 中的默认站点表，并移除对它的依赖。

### 插件运行时模型扩展

扩展 `PluginSiteManifest.metadata` 的使用规范，让插件可以声明默认配置。

如果需要提升可读性，可以后续把这些字段从 `metadata` 中结构化提升到 `PluginSiteManifest` 顶层，但这不是本次必须项。

### 目录聚合逻辑

以下场景统一改为使用 effective catalog：

1. 站点设置页
2. 站点图标与站点列表
3. cookies 上传与拆分
4. cookie 文件匹配
5. 登录状态检测
6. 单站点/批量连通性测试
7. 缩略图下载与离线策略
8. 其他依赖 `SiteCatalog.get_catalog()` 的路径

## Breaking Change

本次明确接受以下破坏性变更：

1. 旧 `config/sites.json` 不迁移
2. 旧 `PUT /api/sites` 请求体不再支持
3. 旧的“保存完整站点列表”逻辑移除
4. 旧的“手工定义一个不存在于插件中的站点”能力移除

落地时需要：

1. 删除旧 `config/sites.json`，或让新保存逻辑直接覆盖为新结构
2. 前端同步切换到新接口格式

## 验证要求

重构完成后至少需要覆盖以下验证：

1. 新插件加载后，无需后端补默认值即可出现在设置页
2. `GET /api/sites` 返回插件默认值和用户 override 合并后的结果
3. `PUT /api/sites` 仅写入 override 字段
4. `config/sites.json` 中不存在未修改字段
5. cookies 上传后，运行时能正确找到对应 `site_cookies/<slug>.txt`
6. 登录检测、订阅导入、连通性测试统一命中 same effective catalog
7. 前端保存一次设置后，不会把默认值物化回文件

## 风险

主要风险有三个：

1. 当前很多路径隐式依赖 `SiteCatalog.get_catalog()`，容易漏改
2. 前端保存逻辑如果没有真正做 diff，仍然会把 effective catalog 直接提交
3. 插件 manifest 中默认配置字段如果定义不统一，不同插件会继续分裂格式

对应控制措施：

1. 全仓库搜索并替换 `SiteCatalog.get_catalog()` 的直接消费点
2. 为 `PUT /api/sites` 增加严格 schema 验证
3. 为插件站点默认配置增加统一测试样例

## 推荐实施顺序

1. 扩展插件站点声明格式，让插件能输出完整默认站点配置
2. 实现 `plugin base catalog`、`override catalog`、`effective catalog`
3. 替换所有后端消费路径到 effective catalog
4. 重写 `/api/sites` 的保存逻辑为 override-only
5. 更新前端设置页提交模型
6. 删除 `site_config_defaults.py` 与旧 `SiteCatalog.get_catalog()` 路径


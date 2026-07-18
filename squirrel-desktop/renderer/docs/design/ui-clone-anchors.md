# UI Clone Anchors（视觉宿主与冻结规则）

← [目录](./README.md) · [Governance](./governance.md)

本文是 **UI 视觉的唯一宿主契约**：Squirrel 全局只使用 **PrimeVue Aura Dark Desktop**
这一套视觉语言。外部产品只能提供信息架构参考，不能再把各自的颜色、密度、控件和
导航样式带入 Squirrel。
合入 UI 相关变更时，本页优先级 **高于**「我觉得再好看一点」类主观调整。

与既有设计系统的关系：

| 层 | 管什么 | 本页是否覆盖 |
|----|--------|----------------|
| [Principles](./principles.md) / [Standards](./standards.md) | Surface、色意、状态闭环 | 不替代；冲突时 **锚点布局优先于自研微调** |
| Foundations / `shared/ui` | token 与控件原子 | **PrimeVue Styled Mode + Aura preset**；`shared/ui` 仅保留产品适配层 |
| **本页** | **全局视觉宿主、页面级 IA 参考、禁止清单、验收方式** | 是 |

---

## 1. 总策略

1. **全应用只认一个视觉宿主**：PrimeVue Aura Dark Desktop。禁止按 Surface 切换视觉语言。
2. **Primitives 冻结**：交互控件来自 PrimeVue；`shared/ui/**` 只做稳定产品 API 与语义映射，禁止复制第二套 Button/Dialog。
3. **日常禁止拧视觉旋钮**（阴影、渐变、圆角微差、侧栏宽、网格 gap 的「感觉」调整）。需要改必须：对照锚点 + 更新本页或 shell/media pattern + 跑视觉验证。
4. **外部产品只供 IA 参考**：FreeTube、YouTube、Fluent Reader、Spotify/YesPlayMusic 可决定栏数、内容顺序和媒体工作流，不得决定组件皮肤。
5. **验收定义**：跨 Surface 的 typography、surface、control、state、motion 必须来自同一 Aura preset；页面布局再对照 IA 参考与冻结尺寸表。

---

## 2. 宿主锚点（唯一表）

| 区域 | 唯一视觉宿主 | IA 参考 | 只参考什么 |
|------|------|--------|----------|
| **应用壳**（Title bar / 侧栏 / 顶栏 / 主滚动区） | **PrimeVue Aura Dark Desktop** | [FreeTube](https://github.com/FreeTubeApp/FreeTube) | 侧栏导航分组、主列结构、内容优先的安静 chrome |
| **视频 Consume**（首页 / 库 / 订阅 / 历史 / 频道 / 网格） | **PrimeVue Aura Dark Desktop** | FreeTube / YouTube Web | 视频网格密度、卡片信息层级、频道页分区 |
| **播放页** | **PrimeVue Aura Dark Desktop** | FreeTube 信息区 + 现有播放器 | 标题区、操作条、相关列表和沉浸关系 |
| **RSS** | **PrimeVue Aura Dark Desktop** | [Fluent Reader](https://github.com/yang991178/fluent-reader) | 源列表 / 条目列表 / 正文三栏 IA |
| **音乐** | **PrimeVue Aura Dark Desktop** | [YesPlayMusic](https://github.com/qier222/YesPlayMusic) / Spotify | 左栏、主内容、贴底全宽三等分播放器 |
| **设置 / 站点 / 定时 / 日志（Operate）** | **PrimeVue Aura Dark Desktop** | PrimeVue Forms / Data | 分区、表单、状态与数据密度 |
| **登录 / 注册** | **PrimeVue Aura Dark Desktop** | PrimeVue Forms | 居中认证面板与单一主行动 |

**主锚点一句话：** 所有 Surface 的视觉 → PrimeVue Aura；外部产品 → 只参考 IA。

---

## 3. 冻结尺寸（工程真源）

以下数值以 **代码 token** 为准；改它们 = 改视觉契约，必须同步本表 + [shell.md](./patterns/shell.md) + 视觉基线。

| 项 | Token / 位置 | 冻结值 |
|----|----------------|--------|
| 桌面标题栏高 | `--app-titlebar-height` | `2rem` |
| 全局顶栏高 | `--app-header-height` | `2.75rem`（quiet chrome） |
| 侧栏展开宽 | `--sidebar-expanded-width` | `15rem` |
| 侧栏项高 | `--sidebar-item-height` | `2.25rem` |
| 侧栏图标 | `--sidebar-icon-size` | `1.25rem` |
| 页边 gutter | `--app-page-gutter*` | `1rem` / `1.5rem` / `2rem` |
| 视频网格 min | `--app-video-grid-min` | `320px` |
| 视频网格 gap | `--app-video-grid-gap*` | `1.5rem` / `1.25rem`×`2.5rem` |
| 视频 Rail 卡宽 | `--app-video-rail-card-width` | `19rem` |
| 视频 Rail gap | `--app-video-rail-gap` | `1.25rem` |
| 音乐网格 min | `--app-music-grid-min` | `180px` |
| 音乐播放器高 | `--app-music-player-height` | `4rem`；Music 页贴底全宽，进度条贴顶，内容三等分 |
| 圆角阶 | `--radius*` | `4–10px` 阶梯，禁止页面私有圆角 |
| 控件库 | `app/main.ts` + `shared/ui/**` | PrimeVue Styled Mode / Aura preset / Lucide（业务图标） |

壳结构标准见 [shell.md](./patterns/shell.md)。媒体卡配方见 [media-craft.md](./patterns/media-craft.md)。

---

## 4. 禁止清单（日常 UI 打磨）

下列变更 **默认拒绝**，除非：有锚点对照依据 + 更新本页/相关 pattern + 更新视觉基线。

- 无功能动机的 token 微调（主色 HSL、阴影层、glow、毛玻璃）
- 业务页私有第二套 Button / 筛选 / 空态 / 卡片，或绕过 Aura semantic token 自制皮肤
- 为「更高级」增加未文档化的 z-index、动画、渐变
- 同时引入多个宿主的视觉语言
- 把 Operate 密度控件铺满 Consume 全页
- 播放器控件换皮（在现有播放器可用的前提下）

---

## 5. 允许清单（应优先投入）

- 订阅 / 同步 / 播放 / 站点会话 / 搜索等 **核心链路**
- 状态闭环：loading / empty / error / 可执行下一步（Spec 3）
- a11y：焦点、键盘、`inert`、必要 aria
- 信息架构与文案（[content.md](./content.md)）
- 用 **shared** 组件替换页面私货

---

## 6. Surface → 宿主速查

| Surface | 典型页 | 视觉宿主 / IA 参考 |
|---------|--------|------|
| Consume | Home、Videos、Play、Music 播放、RSS 正文 | Aura / 对应媒体产品 IA |
| Organize | 订阅管理、播放列表整理、RSS 源树 | Aura / FreeTube、Fluent Reader IA |
| Operate | Settings、Site runtime、Scheduled tasks、Logs | Aura / PrimeVue Forms、Data IA |

3. 产品能力变更 → 根 [README](../../../../README.md)，不在本页复制功能清单

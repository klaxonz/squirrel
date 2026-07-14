# UI Clone Anchors（视觉宿主与冻结规则）

← [目录](./README.md) · [Governance](./governance.md) · [Visual verification](./visual-verification.md)

本文是 **UI 视觉的唯一宿主契约**：好看 = 像锚点产品，而不是继续自研审美。
合入 UI 相关变更时，本页优先级 **高于**「我觉得再好看一点」类主观调整。

与既有设计系统的关系：

| 层 | 管什么 | 本页是否覆盖 |
|----|--------|----------------|
| [Principles](./principles.md) / [Standards](./standards.md) | Surface、色意、状态闭环 | 不替代；冲突时 **锚点布局优先于自研微调** |
| Foundations / `shared/ui` | token 与控件原子 | 继续用 **shadcn-vue new-york + lucide** |
| **本页** | **页面级构图宿主、禁止清单、验收方式** | 是 |

---

## 1. 总策略

1. **每个 Surface 区域只认一个宿主 UI**，禁止「YouTube 侧栏 + Spotify 底栏 + Notion 设置」混搭当日常审美源。
2. **Primitives 冻结**：`shared/ui/**` = shadcn-vue **new-york** + **lucide**；不换组件库、不另起第二套 Button/Dialog。
3. **日常禁止拧视觉旋钮**（阴影、渐变、圆角微差、侧栏宽、网格 gap 的「感觉」调整）。需要改必须：对照锚点 + 更新本页或 shell/media pattern + 跑视觉验证。
4. **允许自由改的**：信息架构、路由、数据绑定、空/错态文案、站点差异字段、真正的功能缺陷。
5. **验收定义**：对照锚点布局与冻结尺寸表；像素级允许 ±2–4px 工程误差；「再圆一点 / 再高级一点」**一律不作为变更理由**。

---

## 2. 宿主锚点（唯一表）

| 区域 | 宿主 | 抄什么 | 不抄什么 |
|------|------|--------|----------|
| **应用壳**（Title bar / 侧栏 / 顶栏 / 主滚动区） | [FreeTube](https://github.com/FreeTubeApp/FreeTube) 桌面布局 | 侧栏导航分组、主列结构、内容优先的安静 chrome | FreeTube 品牌色、图标字体、站点特有逻辑 |
| **视频 Consume**（首页 / 库 / 订阅 / 历史 / 频道 / 网格） | FreeTube +（结构参考）YouTube Web | 视频网格密度、卡片信息层级、频道页分区 | YouTube 广告、推荐算法 UI、品牌红 |
| **播放页** | FreeTube 信息区 + **Artplayer / 现有播放器默认控件气质** | 标题区 + 操作条 + 相关列表；控件可读、不花 | 自研第二套进度条皮肤、炫光 overlay |
| **RSS** | [Fluent Reader](https://github.com/yang991178/fluent-reader) 三栏 | 源列表 / 条目列表 / 正文阅读 | 任意第四种阅读器布局 |
| **音乐** | [YesPlayMusic](https://github.com/qier222/YesPlayMusic) / Spotify 桌面壳 | 左栏 + 主内容 + **底栏播放器** | 与视频壳冲突的第二套全局导航 |
| **设置 / 站点 / 定时 / 日志（Operate）** | [shadcn-vue](https://www.shadcn-vue.com/) dashboard / blocks | 表格、表单、状态徽章、分区标题 | 消费端媒体大卡铺满设置页 |
| **登录 / 注册** | shadcn-vue Auth 模板 | 居中卡片、字段、主按钮 | 独立插画体系、每主题一套登录特效 |

**主锚点一句话：** 视频与壳 → FreeTube；RSS → Fluent Reader；音乐 → YesPlayMusic；Operate → shadcn dashboard；原子 → shadcn-vue new-york。

---

## 3. 冻结尺寸（工程真源）

以下数值以 **代码 token** 为准；改它们 = 改视觉契约，必须同步本表 + [shell.md](./patterns/shell.md) + 视觉基线。

| 项 | Token / 位置 | 冻结值 |
|----|----------------|--------|
| 桌面标题栏高 | `--app-titlebar-height` | `2rem` |
| 全局顶栏高 | `--app-header-height` | `3.25rem` |
| 侧栏展开宽 | `--sidebar-expanded-width` | `15rem` |
| 侧栏项高 | `--sidebar-item-height` | `2.25rem` |
| 侧栏图标 | `--sidebar-icon-size` | `1.25rem` |
| 页边 gutter | `--app-page-gutter*` | `1rem` / `1.5rem` / `2rem` |
| 视频网格 min | `--app-video-grid-min` | `280px` |
| 视频网格 gap | `--app-video-grid-gap*` | `1.5rem` / `1.25rem`×`2.5rem` |
| 视频 Rail 卡宽 | `--app-video-rail-card-width` | `18rem` |
| 视频 Rail gap | `--app-video-rail-gap` | `1.25rem` |
| 音乐网格 min | `--app-music-grid-min` | `180px` |
| 圆角阶 | `--radius*` | `4–10px` 阶梯，禁止页面私有圆角 |
| 控件库 | `components.json` | shadcn-vue **new-york** / **neutral** / lucide |

壳结构标准见 [shell.md](./patterns/shell.md)。媒体卡配方见 [media-craft.md](./patterns/media-craft.md)。

---

## 4. 禁止清单（日常 UI 打磨）

下列变更 **默认拒绝**，除非：有锚点对照依据 + 更新本页/相关 pattern + 更新视觉基线。

- 无功能动机的 token 微调（主色 HSL、阴影层、glow、毛玻璃）
- 业务页私有第二套 Button / 筛选 / 空态 / 卡片
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

| Surface | 典型页 | 宿主 |
|---------|--------|------|
| Consume | Home、Videos、Play、Music 播放、RSS 正文 | FreeTube / YesPlayMusic / Fluent Reader |
| Organize | 订阅管理、播放列表整理、RSS 源树 | FreeTube 列表 + Fluent 源栏 |
| Operate | Settings、Site runtime、Scheduled tasks、Logs | shadcn dashboard |

---

## 7. 变更流程（UI）

```
需求
 → 是否功能/状态/a11y？ 是 → 正常实现，尽量不改冻结尺寸
 → 是否「更好看」？     是 → 对照 §2 宿主；无锚点依据则关闭
 → 必须改布局/token？   → 更新本页 + shell/media 文档 + 视觉基线
 → 跑 visual verification（见 visual-verification.md）
 → 合入
```

---

## 8. 评审话术（固定）

| 评论 | 处理 |
|------|------|
| 「再精致一点」 | 要求指出锚点截图差异；否则不做 |
| 「参考 A 和 B 混一下」 | 拒绝；只允许单一宿主 |
| 「设计系统再扩一章」 | 先问是否锚点已覆盖；优先复刻而非扩写 |
| 「和 FreeTube 不一致」 | 以本页宿主为准修布局，不发明第三种 |

---

## 9. 修订本页

1. 换宿主或冻结尺寸 → 改本页 + 相关 pattern + 视觉基线同一变更集
2. 仅改口号不改验收与基线 → 视为未完成
3. 产品能力变更 → 根 [README](../../../../README.md)，不在本页复制功能清单

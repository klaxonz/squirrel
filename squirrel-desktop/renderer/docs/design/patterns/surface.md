# Surface（场景密度）

← [Patterns](./README.md)

**规格：** [Standards · Spec 1](../standards.md#spec-1--surface)  
**原则：** [P1 内容优先](../principles.md#p1--内容与真实状态优先) · [P5 可预期](../principles.md#p5--一致即可预期)

Surface 描述**界面工作类型对应的密度与强调规格**，不是产品路径分级。  
选定方式：看用户在本区域的主停留行为。

## 三种 Surface

| Surface | 何时用 | 控件高 | 主行动 | 选中 / 当前 | 层次手段 |
|---------|--------|--------|--------|-------------|----------|
| **Consume** | 以观看、收听、阅读为主 | chrome 轻；CTA 可用 Comfort 40px | 每页 1 个 primary（播放 / 主 CTA） | `--app-selection-*` | 同色温 scrim、封面对比、`shadow-card-hover` 抬升 |
| **Organize** | 以订阅、筛选、标记、整理列表为主 | 工具栏 / 筛选 **32px** Dense | 每页 1 个 primary | `--app-selection-*` | hairline 分区 |
| **Operate** | 以配置、任务、日志、站点运维为主 | 表单字段 **36px** Default | 按表单提交需要 | `--app-selection-*` | 语义色 + 字阶 |

## 如何选定

| 主停留行为 | Surface |
|------------|---------|
| 看 / 听 / 读 | Consume |
| 订 / 筛 / 标 / 整理列表 | Organize |
| 改配置 / 修站点与任务 / 看日志 | Operate |

**混合页：** 以主停留区域定 Surface；次区域用对应控件高（例：Consume 页内筛选条 = Organize 32px）。

## 组件来源

按钮、筛选、空态、工具栏 class 必须来自 `shared/ui` 与已文档化 Pattern。  
新能力先扩展 shared，再被业务引用。

## 当前应用：页面 → Surface

路由落地表（改路由时同步更新）：

| 页面 / 区域 | Surface |
|-------------|---------|
| 首页、视频库墙、播放器 | Consume |
| 音乐、RSS 阅读 | Consume |
| 订阅工作台、筛选条、历史、播放列表 | Organize |
| 站点、定时任务、日志、设置 | Operate |

壳结构 → [Shell](./shell.md)

## 与 Media craft

Consume 的密度与强调见上表；**媒体如何排才达到品质下限**见 [Media craft](./media-craft.md)。  
两者都要满足：Surface 管场景规格，Media craft 管卡/墙/首页 rail 配方。

## 验收

- [ ] 可指出 Surface
- [ ] 控件高 / 主行动 / 选中符合上表
- [ ] 无第二套私有 Button / 筛选 / 空态
- [ ] Operate 未统治 Consume / Organize 整页
- [ ] 媒体面勾选 Media craft

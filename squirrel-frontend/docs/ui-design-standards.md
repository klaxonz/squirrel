# Frontend UI Design Standards

本项目保留现有的暗色/科技感/视频工具风格，不把界面改成通用 SaaS 风。统一标准主要控制页面骨架、密度、圆角层级、空状态和 toolbar 行为。

## Layout

- 页面横向留白统一使用 `--app-page-gutter`、`--app-page-gutter-sm`、`--app-page-gutter-lg`。
- 页面主内容顶部留白使用 `--app-content-padding-top`，底部留白使用 `--app-content-padding-bottom`。
- 顶部工具栏垂直密度使用 `--app-toolbar-padding-block`。

## Radius

- 控件和紧凑标签使用 `--app-control-radius` / `--app-control-item-radius`。
- 普通页面 surface、空状态、列表容器使用 `--app-surface-radius`。
- 大型设置卡、主题预览卡、强调型配置卡使用 `--app-feature-card-radius`。

## Empty States

- 空状态保留现有 mono uppercase eyebrow 风格。
- 空状态高度、间距、边框透明度、正文宽度使用 `--app-empty-*` 与 `--app-eyebrow-*`。
- 不为不同页面单独发明空状态布局，除非业务确实需要额外信息结构。

## Toolbar

- Feed、订阅、历史、插件、日志、任务页面的 toolbar 应共享页面 gutter 和 `--app-toolbar-padding-block`。
- 分段切换控件使用 `--app-control-bg`、`--app-control-hover-bg`、`--app-control-active-bg`、`--app-control-shadow`。
- 保留小号、uppercase、mono 的工具风格；不要为了统一改成大号常规按钮。

## Scope

- 先统一标准值和重复结构，不重写页面视觉。
- 页面可以有不同业务布局，但同类元素的尺寸、半径、留白和状态表达必须来自同一组 token。

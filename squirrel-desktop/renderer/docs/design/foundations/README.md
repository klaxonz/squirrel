# Foundations

← [目录](../README.md)

| 页 | 内容 | 代码 |
|----|------|------|
| [color.md](./color.md) | 语义色、选中、scrim | `themes/dark.css` · `layout.css` |
| [typography.md](./typography.md) | 字体与字阶 | `layout.css` · `index.css` |
| [spacing.md](./spacing.md) | 间距、圆角、密度 | `layout.css` |
| [elevation.md](./elevation.md) | 阴影、z-index、单画布 | `layout.css` |
| [motion.md](./motion.md) | 时长与 easing | `layout.css` |

全局 token 速查 → [tokens.md](../tokens.md)  
强制规格 → [Standards](../standards.md)

## Token 分层

对齐常见设计系统（如 Material 的 reference / system / component）的三层模型。业务代码**只消费 system（及文档化的 component 绑定）**，不写死 reference 裸值。

```
Reference          System                 Component
原始阶 / 原始色  →  语义角色 token    →   控件上的绑定
H28 色阶           --primary              Button default → primary
                   --app-selection-*      .is-active → selection
                   --background           页画布
```

| 层 | 是什么 | 存在哪里 | 谁改 |
|----|--------|----------|------|
| **Reference** | 色相阶、灰度阶、未赋予业务含义的原始值 | 主要在 `themes/dark.css` 的通道值；品牌 stop 等 | 主题 / 品牌调整 |
| **System** | 有意图的角色：`primary`、`selection`、`success`、字阶、间距、z | `dark.css` + `layout.css` | 设计规格变更 |
| **Component** | 某控件使用哪个 system token、何种状态 | `shared/ui/**`、layout class、组件文档 | 改组件时同步文档 |

### 规则

1. 业务 Vue/CSS：使用 `hsl(var(--primary))`、`var(--app-selection-bg)` 等 **system** 名。  
2. 需要新语义：先加 system token 与 foundations 文档，再在组件绑定。  
3. 不要为单组件发明与 system 平行的「几乎 primary」色。  
4. 选中与主行动是不同 system 角色：selection 独立于 primary，见 [Color](./color.md) 与 [Spec 2](../standards.md#spec-2--色意映射)。

### 示例

| 需求 | Reference | System | Component |
|------|-----------|--------|-----------|
| 主按钮底 | H28 高饱和琥珀阶 | `--primary` | `Button` `default` |
| 侧栏当前项 | foreground 通道 | `--app-selection-bg` | `.sidebar-item.is-active` |
| 封面压字 | overlay / background | `hsl(var(--overlay) / α)` | Home / 卡片 scrim 类 |

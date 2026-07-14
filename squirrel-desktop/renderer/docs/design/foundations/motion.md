# Motion

← [Foundations](./README.md)

**代码：** `src/shared/styles/layout.css`  
**规格：** [Spec 4](../standards.md#spec-4--视觉系统一致性)

| Token | 值 | 场景 |
|-------|-----|------|
| `--duration-fast` | 120ms | hover、focus、开关 |
| `--duration-base` | 180ms | 面板、页内过渡 |
| `--duration-slow` | 240ms | 大表面 |

- 曲线：`--ease-default` / `--ease-out`。
- 按压：`scale(0.985)`。
- 禁用：`opacity: 0.4`（`--app-field-disabled-opacity`）。
- **必须**尊重 `prefers-reduced-motion`。
- 动效服务状态反馈，不做装饰性入场大秀。

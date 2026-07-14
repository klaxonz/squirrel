以下规则必须严格执行：
1. 所有代码必须按最佳实践编写、修改、评审
2. 编写任何功能、修复任何Bug都不能妥协，一定要找到最根本的原因，从源头解决，不管改动有多大，影响面有多广
3. 一旦开始就一步到位改完，不要工作到一半停下来询问
4. 如果有开源替代方案或者依赖库最好不要自己实现
5. UI 视觉以 [UI Clone Anchors](squirrel-desktop/renderer/docs/design/ui-clone-anchors.md) 为唯一宿主契约：好看 = 像锚点，禁止无锚点依据的日常微调
6. UI 分析 / 一致性评审以代码 + 锚点文档为主；**布局合入**须按 [Visual verification](squirrel-desktop/renderer/docs/design/visual-verification.md) 用 **真实 Electron + CDP**（`npm run visual:check`，默认 `VISUAL_DRIVER=electron`）做截图契约。baseline PNG **仅本地生成、不提交**。禁止用独立浏览器冒充桌面验收，禁止用截图做开放式审美打磨

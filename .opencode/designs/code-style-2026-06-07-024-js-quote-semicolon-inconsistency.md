# 统一 JS/TS 引号与分号风格

## 根因
squirrel-extension 是唯一使用双引号 + 保留分号 + .then() 的子项目，其余（frontend/desktop/music-api）均使用单引号 + 省略分号 + async/await。

## 修复思路
将 extension 全部 .js 文件（5 个）统一为项目主流风格：
- 双引号 → 单引号
- 删除分号
- background.js 中 .then() → async/await（其余文件已使用 async/await，无需修改）

## 涉及文件
- `squirrel-extension/background.js` — 引号 + 分号 + .then() → async/await
- `squirrel-extension/popup.js` — 引号 + 分号
- `squirrel-extension/options.js` — 引号 + 分号
- `squirrel-extension/utils.js` — 引号 + 分号
- `squirrel-extension/config.js` — 引号 + 分号

## 潜在风险
- 纯风格变更，无逻辑改动
- extension 没有测试套件，需 Chrome runtime 验证；但 style-only 改动不改变行为
- background.js 的 async/await 重构需注意 `chrome.runtime.onMessage` 的 `return true` 模式

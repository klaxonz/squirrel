---
title: shell.openExternal 未校验 URL 协议可被用于打开本地文件
status: open
severity: medium
category: security
location: squirrel-desktop/src/ipc-window.mjs:12
---

## 问题描述

`desktop:open-external` IPC handler 只检查 URL 非空就直接传给 `shell.openExternal`。依据 Electron 安全指南，`shell.openExternal` 应校验 URL 协议。攻击者若能控制渲染进程（如 XSS），可传入 `file:///C:/Windows/System32/...` 或其他危险协议。

## 影响

- 潜在的任意文件打开
- 结合渲染进程漏洞可导致信息泄露

## 建议方向

只允许 `https:` 和 `http:` 协议。拒绝 `file:`、`javascript:`、`data:` 等危险 scheme。

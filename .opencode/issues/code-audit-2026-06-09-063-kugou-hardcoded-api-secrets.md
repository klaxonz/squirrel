---
title: KuGou Music API 硬编码 WeChat 密钥和签名密钥
status: open
severity: high
category: security
location: squirrel-music-api/node_modules/kugoumusicapi/util/config.json:3-5; squirrel-music-api/node_modules/kugoumusicapi/util/helper.js:10,26,53,72,83,97; squirrel-music-api/node_modules/kugoumusicapi/util/crypto.js:4-5
---

## 问题描述

KuGou 音乐 API 依赖包中硬编码了大量敏感凭证：

1. **`config.json:3-5`** — WeChat 小程序 `wx_appid`、`wx_lite_appid`、`wx_secret`、`wx_lite_secret` 明文存放。这些 OAuth 凭证可被用于冒充小程序。

2. **`helper.js`** — 6 处 API 签名密钥硬编码：`NVPh5oo715z5DIWAeQlhMDsWXXQV4hwt`（web）、`OIlwieks28dk2k092lksi2UIkp`（Android）、`LnT6xpN3khm36zse0QzvmgTZ3waWdRSA`（lite）、`R6snCXJgbCaj9WFRJKefTMIFp0ey6Gza`（sign）、以及两个 signKey 盐值。

3. **`crypto.js:4-5`** — 两个 RSA 公钥内嵌源码。

## 影响

虽然这些在 `node_modules` 中（第三方包的内部实现），但：
- 凭证明文暴露在代码仓库中
- 任何有仓库访问权限的人可获得这些密钥
- WeChat secret 泄露可被用于冒充应用

## 建议方向

- 将敏感凭证移至环境变量或 `.env` 文件（不加入版本控制）
- 评估是否可将 KuGou 依赖包迁移至 npm（支持 integrity check）而非 GitHub archive
- 在 `.gitignore` 或 `.npmrc` 中确保 `node_modules` 不含凭证文件
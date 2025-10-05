# 订阅自动导入功能

## 功能概述

这个功能允许用户从各个视频站点批量导入已有的订阅，无需手动逐个添加。系统会使用用户的 cookies（通过 CookieCloud 同步）来获取用户在各个站点的订阅列表，然后自动批量导入。

## 支持的站点

- ✅ **Bilibili**：导入关注的 UP 主
- ✅ **YouTube**：导入订阅的频道
- ✅ **Pornhub**：导入订阅的频道、模特和演员
- ✅ **JavDB**：导入订阅的演员

## API 接口

### 导入订阅

```http
POST /api/subscription/import/{site}
```

#### 参数

- `site`: 站点名称，可选值：`bilibili`、`youtube`、`pornhub`、`javdb`

#### 请求头

需要包含认证 token（自动处理）

#### 响应示例

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "site": "bilibili",
    "total": 50,
    "success": 48,
    "failed": 0,
    "skipped": 2,
    "errors": []
  }
}
```

#### 响应字段说明

- `site`: 站点名称
- `total`: 找到的订阅总数
- `success`: 成功导入的数量
- `failed`: 导入失败的数量
- `skipped`: 跳过的数量（已存在的订阅）
- `errors`: 错误信息列表（最多返回前 10 条）

## 使用方法

### 1. 确保 Cookies 已同步

在使用导入功能前，确保已配置 CookieCloud 并成功同步了各站点的 cookies。

配置项（`core/config.py`）：
```python
COOKIE_CLOUD_URL = "你的 CookieCloud 服务地址"
COOKIE_CLOUD_UUID = "你的 UUID"
COOKIE_CLOUD_PASSWORD = "你的密码"
COOKIE_CLOUD_DOMAIN = "bilibili.com,youtube.com,pornhub.com,javdb.com"
```

### 2. 调用导入接口

**从 Bilibili 导入：**
```bash
curl -X POST "http://your-backend/api/subscription/import/bilibili" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**从 YouTube 导入：**
```bash
curl -X POST "http://your-backend/api/subscription/import/youtube" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**从 Pornhub 导入：**
```bash
curl -X POST "http://your-backend/api/subscription/import/pornhub" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**从 JavDB 导入：**
```bash
curl -X POST "http://your-backend/api/subscription/import/javdb" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. 查看导入结果

导入完成后，可以通过订阅列表接口查看导入的订阅：

```bash
curl -X GET "http://your-backend/api/subscription/list?page=1&pageSize=20" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 技术架构

### 1. SDK 层 (`squirrel-sdk`)

- **接口定义**：`IUserSubscriptionImporter` - 定义了获取用户订阅列表的标准接口
- **注册机制**：`UserSubscriptionImporterRegistry` - 管理各站点的 importer 实现
- **装饰器**：`@register_user_subscription_importer` - 用于注册 importer

### 2. 插件层 (`squirrel-plugins`)

每个站点插件都实现了对应的 `importer.py`：

- **Bilibili**：`BilibiliUserSubscriptionImporter`
  - 调用 B 站 API 获取用户关注列表
  - API: `/x/relation/followings`

- **YouTube**：`YoutubeUserSubscriptionImporter`
  - 解析 YouTube 订阅页面获取频道列表
  - 使用正则表达式提取 channelId

- **Pornhub**：`PornhubUserSubscriptionImporter`
  - 爬取订阅的频道、模特、演员页面
  - 支持分页获取完整列表

- **JavDB**：`JavdbUserSubscriptionImporter`
  - 爬取订阅的演员列表
  - 支持分页获取完整列表

### 3. 后端层 (`squirrel-backend`)

- **Service**：`subscription_service.import_user_subscriptions()`
  - 根据站点名称获取对应的 importer
  - 调用 importer 获取订阅列表
  - 批量处理订阅（去重、创建）
  - 返回统计结果

- **Route**：`POST /api/subscription/import/{site}`
  - 参数验证
  - 用户认证
  - 调用 service 层处理
  - 返回统一格式响应

## 工作流程

```
1. 用户调用 API → POST /api/subscription/import/bilibili
                    ↓
2. Route 层验证   → 检查站点是否支持
                    → 验证用户身份
                    ↓
3. Service 层处理 → 获取对应站点的 Importer
                    → 调用 importer.get_user_subscriptions()
                    ↓
4. Plugin 层执行  → 使用 cookies 访问站点 API/页面
                    → 解析获取订阅列表 URL
                    → 返回订阅 URL 列表
                    ↓
5. Service 层处理 → 遍历 URL 列表
                    → 对每个 URL 调用 handle_subscribe_request()
                    → 去重检查
                    → 创建订阅记录
                    ↓
6. 返回结果       → 统计成功/失败/跳过数量
                    → 返回给前端
```

## 错误处理

### 常见错误及解决方法

1. **"No importer found for site: xxx"**
   - 原因：站点名称不正确或该站点未实现 importer
   - 解决：检查站点名称是否在支持列表中

2. **"User not logged in or cookies expired"**
   - 原因：Cookies 未同步或已过期
   - 解决：重新登录站点，等待 CookieCloud 同步

3. **"Failed to get user info"**
   - 原因：站点 API 返回错误或网络问题
   - 解决：检查网络连接，确认站点是否正常访问

4. **大量失败记录**
   - 原因：可能是订阅 URL 格式变化或站点 API 更新
   - 解决：查看日志中的详细错误信息，可能需要更新插件代码

## 性能考虑

1. **批量处理**：导入是同步进行的，大量订阅可能需要较长时间
2. **去重检查**：已存在的订阅会被跳过，不会重复创建
3. **错误容错**：单个订阅失败不会影响其他订阅的导入

## 后续优化建议

1. **异步处理**：将导入任务放入消息队列，支持大量订阅的异步处理
2. **进度通知**：通过 WebSocket 实时推送导入进度（已在 TODO）
3. **增量同步**：定期自动检查新增订阅并同步
4. **错误重试**：对失败的订阅自动重试
5. **批量操作**：支持一次性从所有站点导入

## 测试建议

1. 先在 Bilibili 测试（API 较稳定）
2. 确保有少量订阅的测试账号
3. 检查导入后的订阅是否正确
4. 验证去重逻辑是否正常工作
5. 测试各种异常情况（无 cookies、网络错误等）


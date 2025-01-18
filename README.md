# Squirrel

Squirrel 是一个视频订阅和下载工具，下载时可以生成nfo文件，以供 Emby / Jellyfin 识别元数据。

## 功能特性

- 多平台支持：目前支持 YouTube 和 Bilibili
- 频道订阅：自动下载订阅频道的最新视频
- 用户友好的Web界面：方便管理订阅和下载
- 浏览器拓展：方便快捷的订阅站点频道
- 视频内容展示：轻松浏览和管理下载的内容
- 定时更新：定时更新订阅频道视频

## 待办事项

- [ ] 扩展支持更多视频平台
- [ ] 实现可自定义的下载参数配置

## 快速开始

### 使用指南

1. 添加订阅：使用Web界面添加YouTube或Bilibili频道URL
2. 管理订阅：在订阅列表中查看和管理您的订阅
3. 浏览最新视频：在"最新视频"页面查看下载的内容
4. 使用浏览器拓展：在支持的网站上快速添加订阅
5. 配置设置：调整下载路径、更新频率等参数

### Docker部署

1. 构建镜像：
   ```bash
   ./build.sh
   ```
2. 运行容器：
   ```bash
   docker compose up -d
   ```

### 浏览器拓展安装

1. 安装浏览器插件
2. 打开浏览器，找到扩展管理，将 squirrel-extension 目录导入到浏览器拓展中

## 贡献

欢迎提交问题报告、功能请求和代码贡献。请查看 [CONTRIBUTING.md](./CONTRIBUTING.md) 了解更多信息。

## 许可

本项目遵循 [MIT License](./LICENSE)。
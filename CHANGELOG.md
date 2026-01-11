# Changelog

本项目的所有重要更改都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.2.1] - 2026-01-11

### Changed

- 完善 README 文档结构和内容

## [1.2.0] - 2026-01-11

### Added

- 每日评论功能 (`src/comment.py`)
  - 自动在随机漫画下发表评论
  - 避免重复评论同一漫画
  - 完成后自动领取积分
- 每日阅读功能 (`src/watch.py`)
  - 自动阅读漫画12分钟
  - 智能跳过无效/付费章节
  - 自动翻页和翻章
  - 完成后自动领取积分
- 共享工具模块 (`src/utils.py`)
  - Cookie 解析和 localStorage 设置
  - 浏览器上下文创建
  - 积分领取功能
- 独立的 GitHub Actions workflows
  - `comment.yml` - 每日评论（北京时间 9:30）
  - `watch.yml` - 每日阅读（北京时间 10:00）

### Changed

- 拆分原 `daily_tasks.py` 为独立模块
- 优化跨域登录状态处理（localStorage 同步）

## [1.1.0] - 2026-01-10

### Added

- 支持多账号签到（最多 5 个账号）
- 通过 `ZAIMANHUA_COOKIE_1`、`ZAIMANHUA_COOKIE_2` 等环境变量配置多账号
- 向后兼容单账号 `ZAIMANHUA_COOKIE` 配置

## [1.0.1] - 2026-01-10

### Changed

- 添加调试信息输出（Cookie 解析数量、页面标题、按钮状态）
- 优化已签到状态检测逻辑
- 按钮禁用时尝试 JavaScript 强制点击
- 失败时保存截图用于调试

### Fixed

- 修复已签到时按钮禁用导致的超时错误

## [1.0.0] - 2026-01-10

### Added

- 初始版本发布
- 支持每天三次自动签到（北京时间 8:00、12:00、20:00）
- 使用 Playwright 模拟浏览器操作
- 通过 Cookie 认证登录状态
- 支持手动触发签到（workflow_dispatch）

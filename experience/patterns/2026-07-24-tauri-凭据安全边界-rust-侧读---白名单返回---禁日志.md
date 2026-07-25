---
title: Tauri 凭据安全边界：Rust 侧读 + 白名单返回 + 禁日志
category: patterns
source_projects: [hermes-desktop]
created: 2026-07-24
applicable_when: Tauri 桌面应用需要读取本地凭据（API key / secret）并传给前端使用
not_applicable_when: 纯 Web 应用（无法访问本地文件系统）或无凭据需求的工具类应用
token_saved_estimate: 500
tags: [tauri, security, credentials, rust, api-key]
---

## 背景
hermes-desktop 需要读取 Anthropic API key、MiniMax API key 等凭据，前端需要用但不能泄露。

## 做法
1. **凭据只在 Rust 侧读**：Rust command 读取 `~/.claude/settings.json` 或 `secrets.json`，前端通过 `invoke` 拿到后即用
2. **不进 localStorage**：凭据不持久化到前端存储，每次需要时重新 invoke
3. **白名单返回字段**：`read_cc_settings` 仅返回 3 个指定 key 的值，不返回完整 env 对象
4. **禁日志输出**：所有 `println!` / `console.log` 禁止输出 api_key，CLAUDE.md 明文约束
5. **dangerouslyAllowBrowser: true 安全**：Tauri webview 不是真浏览器，CORS 不适用，凭据在本机不经过外部网络
6. **secrets.json 走 Rust env**：不通过命令行参数传递（避免进程参数泄露），Rust 侧读文件后注入 env

## 反例
- ❌ 凭据存 localStorage → webview XSS 可读取，DevTools 可见
- ❌ `read_cc_settings` 返回完整 env 对象 → 意外泄露其他环境变量
- ❌ `println!` 打印 settings 对象 → 日志文件中可见 api_key
- ❌ 命令行参数传 API key → `ps aux` 可见进程参数

## 验证
- 前端 DevTools 的 localStorage / sessionStorage 中无 api_key
- Rust 日志输出中无 api_key 字符串（grep 验证）
- `read_cc_settings` 返回值只包含 3 个白名单 key
- `dangerouslyAllowBrowser: true` 在 Tauri 上下文中安全（本地 webview，非公网浏览器）

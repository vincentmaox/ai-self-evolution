---
title: Tauri webview 中 dangerouslyAllowBrowser 安全边界判定
category: patterns
source_projects: [hermes-desktop]
created: 2026-07-24
applicable_when: Tauri 应用前端直接调用 Anthropic/OpenAI SDK，需要判定是否开启 `dangerouslyAllowBrowser: true`
not_applicable_when: 纯浏览器 Web 应用；Electron 应用（有不同的安全模型）；Tauri 应用但 API 调用走 Rust 侧 reqwest
token_saved_estimate: 2500
tags: [tauri, security, anthropic-sdk, cors, credential]
---

## 背景
hermes-desktop 前端直接用 `@anthropic-ai/sdk` 调用 Claude API。SDK 默认拒绝在浏览器环境运行（CORS + 凭据泄露风险），但 Tauri webview 不是真浏览器。

## 做法
1. **开启 `dangerouslyAllowBrowser: true`**：Tauri webview 的 origin 是 `tauri://localhost`，不是 `https://`，CORS 策略不适用。
2. **凭据从 Rust 侧读取**：用 Tauri `invoke` 调 Rust command 读 `~/.claude/.credentials.json` 或环境变量，前端拿到后存在内存变量中，**不写 localStorage**。
3. **command 返回最小字段集**：`read_cc_settings` 只返回 3 个 key 的值（如 api_key、base_url、model），不返回完整 env 对象。
4. **日志脱敏**：所有 `println!` / `console.log` 禁止输出 api_key，用 `mask_key()` 统一处理。

## 反例
把 api_key 存入 localStorage 方便下次直接读。后果：Tauri webview 的 localStorage 可被 DevTools 直接查看，且 webview 漏洞可导致凭据泄露。

## 验证
DevTools 中 `localStorage` 为空或不含 api_key。Rust command 返回值用 `serde_json` 序列化后确认不含多余字段。

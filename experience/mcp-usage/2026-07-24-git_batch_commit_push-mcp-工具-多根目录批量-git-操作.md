---
title: git_batch_commit_push MCP 工具：多根目录批量 git 操作
category: mcp-usage
source_projects: [hermes-desktop]
created: 2026-07-24
applicable_when: 需要在一个 MCP 工具调用中扫描多个项目根目录并批量执行 git add/commit/push
not_applicable_when: 单仓库操作，或项目间 git 操作无关联无需批量
token_saved_estimate: 400
tags: [mcp, git, batch, multi-root, project-management]
---

## 背景
hermes-desktop 需要管理 70 个项目（01_Project 目录下），逐个 git commit + push 不可行。

## 做法
1. **MCP 工具封装**：在 in-process MCP 工具集中实现 `git_batch_commit_push`，一次调用扫描所有项目根目录
2. **多根目录扫描**：配置根目录列表，工具自动遍历每个 `.git` 仓库
3. **与项目注册表联动**：`query_projects` 工具先查出所有项目，`git_batch_commit_push` 对有变更的项目执行操作
4. **结果汇总返回**：返回每个项目的操作结果（success/skipped/failed），前端展示汇总
5. **配合 status 归一化**：`update_project_status` 工具中英文状态统一，避免 status 字段混乱

## 反例
- ❌ 逐项目手动 git → 70 个项目要操作 70 次，耗时不可接受
- ❌ 用 shell 脚本批量 git → 无法在 MCP 对话中调用，脱离 AI 工作流
- ❌ 不做结果汇总 → 用户不知道哪些成功哪些失败

## 验证
- `git_batch_commit_push` 一次调用处理 70 个项目
- `query_projects` 返回项目列表，可与 batch 操作联动
- 9 个 in-process MCP 工具覆盖项目查询/写入/状态更新/飞书通知/批量 git

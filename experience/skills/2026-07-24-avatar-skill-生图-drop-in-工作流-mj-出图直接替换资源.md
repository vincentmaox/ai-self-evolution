---
title: avatar skill 生图 drop-in 工作流：MJ 出图直接替换资源
category: skills
source_projects: [hermes-desktop]
created: 2026-07-24
applicable_when: 需要为桌面应用生成角色头像/图标，且用户（非设计师）需要参与选图决策
not_applicable_when: 使用现成 icon set 无需定制；有专业设计师直接出 SVG/PNG 源文件
token_saved_estimate: 2000
tags: [avatar, midjourney, asset, skill, drop-in]
---

## 背景
hermes-desktop 需要老赫人格头像，调用 avatar skill 12 次迭代选图。首次触发时 skill 执行了完整 MJ prompt 生成 -> 下载 -> 放入 assets 目录的流程。

## 做法
1. **skill 触发时机**：在 CLAUDE.md 或对话中提到「头像」「avatar」「生图」「MJ」时触发，不要在架构设计阶段触发。
2. **MJ prompt 模板**：`<角色描述>, <风格关键词>, <尺寸参数 --ar 1:1 --v 6>, <负面词 --no text, watermark>`
3. **多候选 drop-in**：一次生成 4 张候选，放入 `src/assets/avatar_candidates/`，让用户点选后移动到 `src/assets/avatar.png`。
4. **选图确认后清理**：用户确认后删除 candidates 目录，只保留最终图，避免 git 仓库膨胀。
5. **skill 复用**：图标类需求（icons skill）同理，但输出目录为 `src/assets/icons/`，文件名按 `icon_<name>.png` 命名。

## 反例
在架构设计阶段就触发 avatar skill，生成了头像但后续 UI 改了 3 版布局，头像尺寸/风格全部不匹配，浪费 3 次 MJ 调用。应在 UI 框架定稿后再触发。

## 验证
最终头像文件存在于 `src/assets/avatar.png`，尺寸 <= 512x512，文件大小 < 200KB。git log 确认 candidates 目录已清理。

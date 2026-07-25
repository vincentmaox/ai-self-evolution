---
project_name: <项目名>
project_path: <绝对路径>
scan_date: YYYY-MM-DDTHH:MM:SS
scan_version: 1
---

# 行为画像：<项目名>

## 1. 项目元信息（从 registry.json 读）
- 状态：<OK/WIP/STALE/ARCH/!>
- 技术栈：<list>
- 优先级：<P0/P1/P2/P3>
- 最后活动：<date>
- 卡点数：<int>

## 2. AI 模型使用
- 主用模型：<model id（如 glm-5.2 / claude-sonnet-4-6）>
- 切换历史：<list of (date, from, to, reason)>
- 月度 token 估算：<int>

## 3. 提示词模式
- 高频 system prompt 摘要：<text>
- 项目专属指令（CLAUDE.md 关键约束）：<list>
- 用户偏好触发词：<list>

## 4. Skill 调用统计
| skill | 调用次数 | 成功率 | 平均 token |
|---|---|---|---|
| <name> | <int> | <float> | <int> |

## 5. MCP 调用统计
| mcp_server | 工具 | 调用次数 | 高频场景 |
|---|---|---|---|
| <server> | <tool> | <int> | <text> |

## 6. 记忆模式
- 项目记忆文件数：<int>
- 主要类型：<user/feedback/project/reference 占比>
- 高频 feedback 主题：<list>

## 7. 踩坑与解决（从 conversation_log 提取）
| 日期 | 问题 | 解决方法 | 是否可复用 |
|---|---|---|---|
| YYYY-MM-DD | <text> | <text> | <bool> |

## 8. Git 活动
- 最近 7 天提交数：<int>
- 主要贡献者：<list>
- 未提交更改：<int>

## 9. 失败案例（探路先遣队候选）
- <list of (date, description, root_cause)>

## 10. 可提炼经验（候选）
- <list of candidate experiences for extractor>

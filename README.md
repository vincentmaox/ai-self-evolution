# ai-self-evolution / 虚空藏经阁

> 老茅（虚空建筑师）的 AI 自进化引擎。让所有 AI Agent 启动时继承跨项目经验。

## 定位

在 ProjectOS 之上叠加"能力层"：扫描所有项目的 AI 行为（用什么模型、调什么 skill/MCP、踩什么坑、怎么解决的），提炼可复用经验，注入到下个项目启动 context。

**目标**：用更少 token 更好解决问题，持续迭代进化。

## 快速上手

```bash
cd D:/ClaudeCodeProjects/ai-self-evolution

# 1. 扫描单项目（生成行为画像）
python -m agents.scanner --project hermes-desktop

# 2. 提炼经验（调 GLM-5.2）
python -m agents.extractor --project hermes-desktop

# 3. 注入到项目记忆
python -m agents.injector --project hermes-desktop

# 或一键跑全流程
python scripts/run_pipeline.py --project hermes-desktop
```

## 架构

```
[新项目启动] ──> injector(分院帽) ──> 项目记忆文件
                       ↑
               [experience/ 经验库]
                       ↑
               [extractor(炼金师) - GLM-5.2]
                       ↑
               [scanner(探路者)] ──> registry + conversation_log + memory
```

## 3 个核心 Agent

| Agent | 角色 | 职责 |
|---|---|---|
| **scanner** | 探路者 | 扫项目对话历史/记忆/CLAUDE.md/git log -> 行为画像 |
| **extractor** | 炼金师 | LLM 提炼可复用经验 -> 经验库 |
| **injector** | 分院帽 | 检索经验 -> 注入项目记忆文件 |

## 经验库

```
experience/
  patterns/    # 解决问题模式（debug/perf/security/i18n/...）
  prompts/     # 提示词模板库
  skills/      # 通用 skill 模板
  mcp-usage/   # MCP 使用经验（lark/playwright/...）
  failures/    # 失败案例（探路先遣队训练数据）
  INDEX.md     # 全局索引
```

## 落地节奏

- **P1 MVP**（24-48h）：骨架 + scanner/extractor/injector 跑通 hermes-desktop 单项目
- **P2 闭环**（72h-1w）：全量扫描 + schtasks 调度 + 3-5 项目接入
- **P3 进化**（1-2w）：反馈环 + 注入优化 + hermes-desktop 可视化 + token 对比

## 安全约束

- LLM 调用走 `claude` CLI subprocess，不直接读 token
- 不 Read 任何 `*.env` / `settings.json` / `*credentials*` 文件
- 输出经验条目禁止包含真实凭据
- 详见 `CLAUDE.md`

## 关联项目

- ProjectOS（项目元数据中枢）：`D:/ClaudeCodeProjects/_ProjectOS/`
- hermes-desktop（桌面端 + 老赫 sidecar）：`D:/ClaudeCodeProjects/hermes-desktop/`
- 全局 CLAUDE.md：`~/.claude/CLAUDE.md`

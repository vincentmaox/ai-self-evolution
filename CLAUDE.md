# 虚空藏经阁 (ai-self-evolution)

## 项目身份

老茅（虚空建筑师）的 **AI 自进化引擎**。在 ProjectOS 之上叠加"能力层"，把"项目做完即忘"升级为"做完提炼 -> 注入下个项目"，让所有 AI Agent 启动时继承跨项目经验。

**目标**：更少 token 解决问题 + 持续迭代进化。

**架构选型**：Python 3 + 纯文件存储（JSON+MD）+ claude CLI subprocess（不碰 token）

## 5 层数据流

```
[新项目启动] ──> injector(分院帽) ──> 项目记忆文件 + 启动推荐
                       ↑
               [experience/ 经验库]
                       ↑
               [extractor(炼金师) - GLM-5.2]
                       ↑
               [scanner(探路者)] ──> registry + conversation_log + memory
```

## 文件清单

```
ai-self-evolution/
  agents/
    scanner.py            # 探路者：扫项目 -> 行为画像
    extractor.py          # 炼金师：LLM 提炼可复用经验
    injector.py           # 分院帽：检索经验 -> 注入项目记忆
    common.py             # 共用工具（路径/LLM调用/索引）
  experience/
    patterns/             # 解决问题模式（debug/perf/security/...）
    prompts/              # 提示词模板库
    skills/               # 通用 skill 模板
    mcp-usage/            # MCP 使用经验（lark/playwright/...）
    failures/             # 失败案例（探路先遣队训练数据）
    INDEX.md              # 全局索引
  data/
    project_profiles/     # 每项目行为画像（JSON，不入 git）
    evolution_log.md      # 进化日志
  scripts/
    run_pipeline.py       # 一键跑 scanner->extractor->injector
  templates/
    profile_template.md   # 行为画像模板
    experience_template.md # 经验条目模板
  CLAUDE.md
  README.md
  .gitignore
```

## 3 个核心 Agent

| Agent | 角色 | 触发 | 输入 -> 输出 |
|---|---|---|---|
| **scanner** | 探路者 | 每日 23:30 增量 + 每周一全量 | conversation_log + memory + CLAUDE.md + git log -> `data/project_profiles/<proj>.json` |
| **extractor** | 炼金师 | 每周一 09:00 | 行为画像 + 同类对比 -> `experience/{patterns,prompts,skills,mcp-usage,failures}/` |
| **injector** | 分院帽 | 项目启动 hook / 手动 CLI | registry 画像 + 经验库检索 -> `~/.claude/projects/<proj>/memory/cross-project-experience.md` |

## 关键架构原则

### 1. 复用 ProjectOS 基础设施
- registry.json（项目元数据）-> 直接读 `D:/ClaudeCodeProjects/_ProjectOS/data/registry.json`
- conversation_log.md（对话历史）-> 直接读项目根目录
- conversation_index.json（全局索引）-> 直接读 `~/.claude/conversation_index.json`
- schtasks 调度 -> 跟 daily_recap.py / thought_inspector.py 同机制

### 2. LLM 调用：claude CLI subprocess
- **不直接读 `~/.claude/settings.json` 的 token**（继承全局密钥安全规则）
- 通过 `claude_agent_sdk` 或直接 `subprocess` spawn `claude` CLI
- CLI 在 spawn 那刻读 settings.json env，token 不进 Python 内存
- 跟 hermes-desktop sidecar 同机制（CC Switch 切换零感知）

### 3. 注入机制：项目记忆文件
- 写到 `~/.claude/projects/<proj>/memory/cross-project-experience.md`
- session 启动自动加载（Claude Code 内建机制）
- 不污染 git 仓
- 灵活可更新（每次 scanner 跑完刷新）

### 4. 不灌水原则
- injector 只注入**高相关**经验（基于项目画像匹配度）
- 经验条目必须有"适用场景 + 不适用场景"
- 避免上下文污染导致 token 浪费

### 5. 纯文件存储
- JSON：行为画像、索引、调度状态
- MD：经验条目、进化日志
- git 可追溯，LLM 直接读

## 安全约束（继承全局）

全局 `~/.claude/CLAUDE.md` 已写入「密钥安全」硬约束。本仓库工作时**额外注意**：

- **禁止 Read 整文件读取** `~/.claude/settings.json` / `_ProjectOS/agent/cc_bot.env` / 任何 `*.env`
- 验证字段存在：`grep -c FIELD_NAME 文件`
- 验证字段非空：`python -c "import json; print(bool(json.load(open(p))['env']['KEY']))"` 只打 True/False
- LLM 调用一律走 `claude` CLI subprocess，不在 Python 里硬编码 token
- 输出经验条目时，禁止包含真实 token / API key / 密码

## 开发工作流

### 新增 Agent
1. 在 `agents/` 下新建 `<name>.py`
2. 入口函数 `run(target_project=None, **kwargs)` -> 返回 dict / 写文件
3. 加 `--help` 和 CLI 入口（`python -m agents.<name> --project xxx`）
4. 在 `scripts/run_pipeline.py` 注册

### 新增经验分类
1. 在 `experience/` 下建子目录
2. 在 `experience/INDEX.md` 加分类条目
3. 在 `templates/experience_template.md` 复用模板

### 经验条目格式
```markdown
---
title: <短标题>
category: patterns | prompts | skills | mcp-usage | failures
source_projects: [proj1, proj2]
created: YYYY-MM-DD
applicable_when: <适用场景>
not_applicable_when: <不适用场景>
token_saved_estimate: <预估节省 token 数>
---

<正文：背景 / 做法 / 反例 / 验证>
```

## 关联

- ProjectOS registry：`D:/ClaudeCodeProjects/_ProjectOS/data/registry.json`
- 对话全局索引：`~/.claude/conversation_index.json`
- 全局记忆：`~/.claude/memory/`
- hermes-desktop：`D:/ClaudeCodeProjects/hermes-desktop/`（参考 sidecar LLM 调用方式）
- 全局 CLAUDE.md：`~/.claude/CLAUDE.md`（密钥安全 + 身份切换 + 决策框架）

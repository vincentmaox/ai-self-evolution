"""
extractor.py - 炼金师：从行为画像提炼可复用经验 -> 经验库

调用 GLM-5.2 (via Anthropic 兼容协议，智谱代理) 提炼经验。
输入：data/project_profiles/<project>.json
输出：experience/<category>/<slug>.md + 更新 INDEX.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from agents import common


SYSTEM_PROMPT = """你是「虚空藏经阁」的炼金师。你的职责是从 AI 项目行为画像中提炼可跨项目复用的经验。

# 提炼原则
1. **不灌水**：每条经验必须可执行，不要写"应该注意 X"这种空话
2. **有边界**：必须明确"适用场景"和"不适用场景"
3. **可复制**：做法要具体到步骤，反例要具体到误用后果
4. **省 token**：每条经验估算每次应用节省的 token 数（基于输入画像规模）

# 经验分类
- `patterns`: 解决问题模式（如「Tauri 全局热键 IME 冲突如何规避」）
- `prompts`: 高效提示词模板（如「架构设计 prompt 结构」）
- `skills`: 通用 skill 使用经验（如「frontend-design skill 何时触发」）
- `mcp-usage`: MCP 工具调用经验（如「lark-mcp bitable 创建记录的字段映射」）
- `failures`: 失败案例（必须含 根因 / 教训 / 可回收资产）

# 输出格式（严格 JSON，不要 markdown 代码块包裹）
{
  "experiences": [
    {
      "category": "patterns|prompts|skills|mcp-usage|failures",
      "title": "<60字以内短标题>",
      "applicable_when": "<适用场景描述>",
      "not_applicable_when": "<不适用场景描述>",
      "tags": ["<tag1>", "<tag2>"],
      "token_saved_estimate": <int>,
      "body": "<markdown 正文，结构：## 背景\\n## 做法\\n## 反例\\n## 验证>"
    }
  ]
}

只输出 JSON，不要任何前后缀说明。"""


def build_prompt(profile: dict) -> str:
    """构造提炼 prompt"""
    name = profile["project_name"]
    cl = profile.get("conversation_log", {})
    cm = profile.get("claude_md", {})
    pm = profile.get("project_memory", {})
    g = profile.get("git", {})

    # Top skills（取前 10）
    skills = sorted(cl.get("skill_calls", {}).items(), key=lambda x: -x[1])[:10]
    skills_text = "\n".join(f"  - {k}: {v} 次" for k, v in skills) or "  （无）"

    # MCP 调用
    mcp_calls = cl.get("mcp_calls", {})
    mcp_text = "\n".join(f"  - {k}: {v} 次" for k, v in mcp_calls.items()) or "  （无）"

    # 模型
    models = cl.get("model_mentions", {})
    models_text = ", ".join(f"{k}({v}次)" for k, v in models.items()) or "未明确提及"

    # 踩坑片段（取前 5 条）
    fix_samples = cl.get("fix_mentions_sample", [])[:5]
    fix_text = "\n\n".join(f"  [{i+1}] {s}" for i, s in enumerate(fix_samples)) or "  （无）"

    # CLAUDE.md 约束
    constraints = cm.get("constraints", [])
    constraints_text = "\n\n".join(f"  ### {i+1}\n  {c}" for i, c in enumerate(constraints[:4])) or "  （无）"

    # 项目记忆摘要
    mem_summaries = pm.get("memory_summaries", [])
    mem_text = "\n".join(
        f"  - [{s.get('type', 'unknown')}] {s.get('name', '')}: {s.get('description', '')[:100]}"
        for s in mem_summaries
    ) or "  （无）"

    # Git
    git_text = f"近 14d 提交 {g.get('commits_14d', 0)} 次，分支 {g.get('branch', '?')}，未提交 {g.get('uncommitted_count', 0)} 项"

    return f"""# 项目行为画像：{name}

## 元信息
- 路径：{profile.get('project_path', '?')}
- 对话 log：{cl.get('total_bytes', 0)} bytes / {cl.get('total_turns', 0)} turns / {cl.get('days_count', 0)} days
- Git：{git_text}

## 模型使用
{models_text}

## CLAUDE.md 关键约束章节
{constraints_text}

## 踩坑与解决片段
{fix_text}

## Skill 调用统计（Top 10）
{skills_text}

## MCP 调用统计
{mcp_text}

## 项目记忆摘要
{mem_text}

---

# 任务

从以上画像提炼 3-6 条可跨项目复用的经验。重点优先级：
1. **失败案例**（failures）- 最高价值，必出
2. **解决问题模式**（patterns）- 高频踩坑的解法
3. **MCP 使用经验**（mcp-usage）- 调用过的工具模式
4. **Skill 使用经验**（skills）- skill 触发时机
5. **提示词模板**（prompts）- 项目里反复用的 prompt 结构
6. **架构原则**（patterns）- 不要踩的坑

输出严格 JSON 格式（见 system prompt）。"""


def extract_json(text: str) -> dict | None:
    """从 LLM 返回中提取 JSON（容忍前后缀说明）"""
    # 找第一个 { 到最后一个 }
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < 0 or end <= start:
        return None
    json_str = text[start : end + 1]
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # 尝试修复常见问题：尾部逗号
        cleaned = re.sub(r",\s*([}\]])", r"\1", json_str)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return None


def extract(project_name: str, dry_run: bool = False, verbose: bool = True) -> list[Path]:
    """提炼经验。返回写入的文件路径列表"""
    profile = common.load_profile(project_name)
    if not profile:
        print(f"[ERROR] 找不到行为画像: {common.PROFILES_DIR / (project_name + '.json')}", file=sys.stderr)
        print(f"        请先跑: python -m agents.scanner --project {project_name}", file=sys.stderr)
        return []

    if verbose:
        print(f"[extractor] 提炼 {project_name} -> 调用 LLM...")

    prompt = build_prompt(profile)
    if dry_run:
        print("\n===== PROMPT =====")
        print(prompt)
        print("\n===== END PROMPT =====")
        return []

    result = common.call_llm(prompt=prompt, system=SYSTEM_PROMPT, max_tokens=8192, timeout=180)

    if not result["ok"]:
        print(f"[ERROR] LLM 调用失败: {result['error']}", file=sys.stderr)
        common.append_log(f"extractor - {project_name} (失败)", [
            f"错误: {result['error']}",
            f"模型: {result['model']}",
        ])
        return []

    if verbose:
        print(f"[extractor] LLM 返回 {len(result['text'])} 字符 / tokens: in={result['tokens_in']} out={result['tokens_out']}")

    parsed = extract_json(result["text"])
    if not parsed or "experiences" not in parsed:
        # 保存原始输出供调试
        debug_path = common.PROJECT_ROOT / "data" / f"extractor_raw_{project_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        debug_path.write_text(result["text"], encoding="utf-8")
        print(f"[ERROR] JSON 解析失败，原始输出: {debug_path}", file=sys.stderr)
        common.append_log(f"extractor - {project_name} (JSON 解析失败)", [
            f"模型: {result['model']}",
            f"tokens: in={result['tokens_in']} out={result['tokens_out']}",
            f"原始输出存于: {debug_path}",
        ])
        return []

    experiences = parsed["experiences"]
    if not isinstance(experiences, list):
        print(f"[ERROR] experiences 不是 list", file=sys.stderr)
        return []

    written: list[Path] = []
    for exp in experiences:
        cat = exp.get("category", "patterns").strip()
        if cat not in {"patterns", "prompts", "skills", "mcp-usage", "failures"}:
            cat = "patterns"
        title = exp.get("title", "untitled").strip()[:80]
        slug = common.slugify(title)
        if not slug:
            slug = f"exp-{datetime.now().strftime('%H%M%S')}"

        # 防止重名（加日期前缀）
        slug = f"{datetime.now().strftime('%Y-%m-%d')}-{slug}"

        path = common.write_experience(
            category=cat,
            slug=slug,
            title=title,
            source_projects=[project_name],
            body=exp.get("body", ""),
            applicable_when=exp.get("applicable_when", ""),
            not_applicable_when=exp.get("not_applicable_when", ""),
            tags=exp.get("tags", []),
            token_saved_estimate=int(exp.get("token_saved_estimate", 0)),
        )
        written.append(path)
        common.update_index(cat, slug, title, [project_name])

        if verbose:
            print(f"  -> [{cat}] {title}")
            print(f"     {path}")

    common.append_log(f"extractor - {project_name}", [
        f"模型: {result['model']}",
        f"tokens: in={result['tokens_in']} out={result['tokens_out']}",
        f"提炼经验条目: {len(written)}",
        *[f"  - [{w.parent.name}] {w.stem}" for w in written],
    ])

    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="炼金师：从行为画像提炼可复用经验")
    parser.add_argument("--project", required=True, help="项目名（如 hermes-desktop）")
    parser.add_argument("--dry-run", action="store_true", help="只打印 prompt，不调 LLM")
    args = parser.parse_args()

    written = extract(args.project, dry_run=args.dry_run)
    if not written:
        return 1
    print(f"\n[extractor] 完成: {len(written)} 条经验写入 experience/")
    return 0


if __name__ == "__main__":
    sys.exit(main())

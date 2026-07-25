"""
injector.py - 分院帽：检索经验库 -> 注入到项目记忆文件

输入：项目名（如 hermes-desktop）
流程：
  1. 读项目行为画像（profile JSON）
  2. 提取项目关键词（技术栈 / skill / mcp / 模型）
  3. 遍历经验库（experience/），按相关性打分
  4. 取 Top N（默认 5）写入项目记忆文件：
     ~/.claude/projects/<encoded>/memory/cross-project-experience.md
  5. Claude Code 下次 session 启动时自动加载

设计原则：
  - 不灌水：只注入高相关经验（score >= MIN_SCORE）
  - 不污染 git 仓：写到 ~/.claude/projects/，不进项目目录
  - 可更新：每次跑刷新（不是追加）
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

from agents import common

MIN_SCORE = 5  # 最低相关性分数，低于此不注入
MAX_EXPERIENCES = 5  # 最多注入条数


def extract_project_keywords(profile: dict) -> set[str]:
    """从项目行为画像提取关键词"""
    keywords: set[str] = set()
    cl = profile.get("conversation_log", {})
    cm = profile.get("claude_md", {})

    # 模型
    for m in cl.get("model_mentions", {}):
        keywords.add(m.lower())

    # Skill 调用
    for s in cl.get("skill_calls", {}):
        keywords.add(s.lower())

    # MCP server
    for s in cl.get("mcp_servers", {}):
        keywords.add(s.lower())

    # CLAUDE.md 约束里的技术栈关键词
    for section in cm.get("constraints", []):
        # 提取英文技术词
        for m in re.finditer(r"\b([a-z][a-z0-9-]{2,})\b", section.lower()):
            word = m.group(1)
            # 过滤常见无意义词
            if word not in {
                "the", "and", "for", "with", "from", "this", "that", "are", "not",
                "but", "you", "all", "any", "can", "has", "have", "more", "when",
                "use", "used", "uses", "using", "via", "into", "out", "get", "set",
                "see", "run", "put", "add", "try", "let", "may", "will", "must",
                "key", "value", "data", "list", "item", "name", "type",
            }:
                keywords.add(word)

    return keywords


def load_experience_index() -> list[dict]:
    """读 experience/ 下所有 .md 经验条目"""
    experiences: list[dict] = []
    for cat_dir in common.EXPERIENCE_DIR.iterdir():
        if not cat_dir.is_dir() or cat_dir.name.startswith("."):
            continue
        for md in cat_dir.glob("*.md"):
            if md.name == "README.md":
                continue
            text = md.read_text(encoding="utf-8", errors="ignore")
            # 解析 frontmatter
            fm_match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
            if not fm_match:
                continue
            fm_text = fm_match.group(1)
            body = text[fm_match.end() :]

            def get_fm(key: str) -> str:
                m = re.search(rf"^{key}:\s*(.+)$", fm_text, re.MULTILINE)
                return m.group(1).strip() if m else ""

            def get_fm_list(key: str) -> list[str]:
                val = get_fm(key)
                # 解析 [a, b, c] 格式
                val = val.strip("[]")
                return [v.strip().strip('"\'') for v in val.split(",") if v.strip()]

            category = cat_dir.name
            source_projects = get_fm_list("source_projects")
            tags = get_fm_list("tags")

            experiences.append({
                "path": md,
                "category": category,
                "title": get_fm("title").strip("\"'"),
                "applicable_when": get_fm("applicable_when").strip("\"'"),
                "not_applicable_when": get_fm("not_applicable_when").strip("\"'"),
                "source_projects": source_projects,
                "tags": tags,
                "token_saved_estimate": int(get_fm("token_saved_estimate") or 0),
                "body": body.strip(),
                "file_name": md.name,
            })

    return experiences


def score_experience(exp: dict, project_name: str, keywords: set[str]) -> int:
    """给经验条目算相关性分"""
    score = 0

    # 同源项目：+10
    if project_name in exp["source_projects"]:
        score += 10

    # tag 命中：+5 每个
    for tag in exp["tags"]:
        if tag.lower() in keywords:
            score += 5

    # title 关键词命中：+3 每个
    title_words = set(re.findall(r"\b([a-z][a-z0-9-]{2,})\b", exp["title"].lower()))
    score += len(title_words & keywords) * 3

    # applicable_when 命中：+2 每个
    app_words = set(re.findall(r"\b([a-z][a-z0-9-]{2,})\b", exp["applicable_when"].lower()))
    score += len(app_words & keywords) * 2

    # failures 类别加权（高价值）：+3
    if exp["category"] == "failures":
        score += 3

    return score


def build_injection_content(
    project_name: str,
    profile: dict,
    selected: list[tuple[dict, int]],
) -> str:
    """构造写入项目记忆的内容"""
    cl = profile.get("conversation_log", {})
    cm = profile.get("claude_md", {})
    pm = profile.get("project_memory", {})
    g = profile.get("git", {})

    # 项目画像摘要
    summary_lines = [
        f"# 跨项目经验注入 - {project_name}",
        "",
        f"> 由 ai-self-evolution injector 自动生成 | {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "> 基于 scanner 行为画像 + 经验库相关性匹配（不灌水原则）",
        "",
        "## 项目行为画像（摘要）",
        "",
        f"- **路径**：{profile.get('project_path', '?')}",
        f"- **对话 log**：{cl.get('total_bytes', 0)} bytes / {cl.get('total_turns', 0)} turns",
        f"- **CLAUDE.md**：{'有 (' + str(cm.get('char_count', 0)) + ' chars)' if cm.get('has_claude_md') else '无'}",
        f"- **Git**：分支 {g.get('branch', '?')} / 近 14d 提交 {g.get('commits_14d', 0)}",
        f"- **项目记忆文件**：{pm.get('memory_files', 0)} ({pm.get('memory_types', {})})",
        "",
    ]

    # 模型
    if cl.get("model_mentions"):
        models = ", ".join(f"`{k}`({v}次)" for k, v in cl["model_mentions"].items())
        summary_lines.append(f"- **模型**：{models}")

    # MCP servers
    if cl.get("mcp_servers"):
        servers = ", ".join(f"`{k}`({v}次)" for k, v in cl["mcp_servers"].items())
        summary_lines.append(f"- **MCP servers**：{servers}")

    # 高频踩坑关键词
    if cl.get("fix_mentions_count"):
        summary_lines.append(f"- **踩坑提及**：{cl.get('fix_mentions_count')} 次")

    summary_lines.extend(["", "---", ""])

    # 推荐经验
    summary_lines.extend([
        "## 推荐跨项目经验（按相关性）",
        "",
        f"> 共匹配到 {len(selected)} 条高相关经验（score >= {MIN_SCORE}，上限 {MAX_EXPERIENCES}）",
        "",
    ])

    for i, (exp, score) in enumerate(selected, 1):
        summary_lines.extend([
            f"### {i}. [{exp['category']}] {exp['title']}",
            "",
            f"- **相关性**：{score} 分",
            f"- **适用**：{exp['applicable_when'][:200]}",
            f"- **不适用**：{exp['not_applicable_when'][:200]}",
            f"- **预估节省**：{exp['token_saved_estimate']} tokens / 次",
            f"- **源项目**：{', '.join(exp['source_projects'])}",
            f"- **tags**：{', '.join(exp['tags']) if exp['tags'] else '无'}",
            f"- **源文件**：`experience/{exp['category']}/{exp['file_name']}`",
            "",
        ])

        # 正文截断（避免太长，每条最多 1500 字符）
        body = exp["body"]
        if len(body) > 1500:
            body = body[:1500] + "\n\n...（截断，完整内容见源文件）"
        summary_lines.extend([body, "", "---", ""])

    # 启动建议
    summary_lines.extend([
        "## 启动建议",
        "",
        "1. **优先验证**：检查推荐经验里有没有当前项目已踩但未修复的坑",
        "2. **回避重蹈**：失败的解法不要再试",
        "3. **复用模式**：high-score patterns 直接套用",
        "4. **更新机制**：每次 scanner+extractor 跑完会刷新本文件",
        "",
        "## 关联",
        "",
        f"- 行为画像：`D:/ClaudeCodeProjects/ai-self-evolution/data/project_profiles/{project_name}.json`",
        f"- 经验库索引：`D:/ClaudeCodeProjects/ai-self-evolution/experience/INDEX.md`",
        f"- 进化日志：`D:/ClaudeCodeProjects/ai-self-evolution/data/evolution_log.md`",
        "",
    ])

    return "\n".join(summary_lines)


def inject(project_name: str, max_count: int = MAX_EXPERIENCES, min_score: int = MIN_SCORE, dry_run: bool = False, verbose: bool = True) -> Path | None:
    """注入经验到项目记忆文件"""
    profile = common.load_profile(project_name)
    if not profile:
        print(f"[ERROR] 找不到行为画像: {common.PROFILES_DIR / (project_name + '.json')}", file=sys.stderr)
        print(f"        请先跑: python -m agents.scanner --project {project_name}", file=sys.stderr)
        return None

    if verbose:
        print(f"[injector] 注入 {project_name}...")

    keywords = extract_project_keywords(profile)
    if verbose:
        print(f"  关键词（{len(keywords)} 个）: {sorted(keywords)[:20]}{'...' if len(keywords) > 20 else ''}")

    experiences = load_experience_index()
    if not experiences:
        print(f"[WARN] 经验库为空，请先跑 extractor", file=sys.stderr)
        return None

    if verbose:
        print(f"  经验库: {len(experiences)} 条")

    # 打分
    scored = [(exp, score_experience(exp, project_name, keywords)) for exp in experiences]
    scored.sort(key=lambda x: -x[1])

    # 筛选 + 截断
    selected = [(exp, score) for exp, score in scored if score >= min_score][:max_count]

    if not selected:
        print(f"[WARN] 没有高相关经验（score >= {min_score}），跳过注入", file=sys.stderr)
        common.append_log(f"injector - {project_name} (无匹配)", [
            f"经验库: {len(experiences)} 条",
            f"关键词: {len(keywords)} 个",
            f"最高分: {scored[0][1] if scored else 0}",
        ])
        return None

    if verbose:
        print(f"  匹配高相关: {len(selected)} 条 (score >= {min_score})")
        for exp, score in selected:
            print(f"    [{score:>2}] [{exp['category']}] {exp['title']}")

    content = build_injection_content(project_name, profile, selected)

    if dry_run:
        print("\n===== INJECTION CONTENT =====")
        print(content[:3000])
        if len(content) > 3000:
            print(f"...（共 {len(content)} 字符，截断显示）")
        return None

    # 写入项目记忆
    from agents.scanner import encode_project_path
    encoded = encode_project_path(Path(profile["project_path"]))

    memory_dir = common.CLAUDE_PROJECTS / encoded / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    out_path = memory_dir / "cross-project-experience.md"

    # 写 frontmatter（项目记忆格式，type=reference）
    frontmatter = f"""---
name: cross-project-experience
description: "由 ai-self-evolution injector 自动注入的跨项目经验推荐 - 基于行为画像匹配"
metadata:
  type: reference
  source: ai-self-evolution
  project: {project_name}
  injected_at: {datetime.now().isoformat(timespec='seconds')}
  experience_count: {len(selected)}
  keywords_count: {len(keywords)}
---

"""
    out_path.write_text(frontmatter + content, encoding="utf-8")

    if verbose:
        print(f"\n[injector] 写入: {out_path}")
        print(f"  文件大小: {out_path.stat().st_size} bytes")

    # 登记 MEMORY.md 索引（让 Claude session 启动时能发现）
    common.ensure_memory_indexed(
        memory_dir=memory_dir,
        file_name="cross-project-experience.md",
        title="Cross-project Experience (auto-injected)",
        description=f"由 ai-self-evolution injector 自动注入的跨项目经验推荐 - {len(selected)} 条高相关经验 (score>={min_score})",
    )

    if verbose:
        print(f"  MEMORY.md 索引已更新")

    common.append_log(f"injector - {project_name}", [
        f"经验库: {len(experiences)} 条",
        f"关键词: {len(keywords)} 个",
        f"注入: {len(selected)} 条 (score >= {min_score})",
        f"写入: {out_path}",
        f"大小: {out_path.stat().st_size} bytes",
        f"MEMORY.md 索引已更新",
    ])

    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="分院帽：检索经验 -> 注入项目记忆")
    parser.add_argument("--project", required=True, help="项目名（如 hermes-desktop）")
    parser.add_argument("--max", type=int, default=MAX_EXPERIENCES, help=f"最多注入条数（默认 {MAX_EXPERIENCES}）")
    parser.add_argument("--min-score", type=int, default=MIN_SCORE, help=f"最低相关性分数（默认 {MIN_SCORE}）")
    parser.add_argument("--dry-run", action="store_true", help="只打印注入内容，不写入")
    args = parser.parse_args()

    result = inject(args.project, max_count=args.max, min_score=args.min_score, dry_run=args.dry_run)
    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())

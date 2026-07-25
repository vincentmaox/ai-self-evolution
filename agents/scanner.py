"""
scanner.py - 探路者：扫描项目 -> 行为画像

扫描源：
  - <project>/conversation_log.md  对话历史
  - <project>/CLAUDE.md             项目硬约束
  - <project>/README.md             项目说明
  - ~/.claude/projects/<encoded>/memory/  项目级记忆
  - ~/.claude/conversation_index.json     全局对话索引
  - <project>/.git                       git 活动

输出：data/project_profiles/<project>.json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROFILES_DIR = PROJECT_ROOT / "data" / "project_profiles"
LOG_FILE = PROJECT_ROOT / "data" / "evolution_log.md"

PROJECTS_ROOT = Path("D:/ClaudeCodeProjects")
REGISTRY_PATH = PROJECTS_ROOT / "_ProjectOS" / "data" / "registry.json"
CLAUDE_HOME = Path.home() / ".claude"
CONVERSATION_INDEX = CLAUDE_HOME / "conversation_index.json"
CLAUDE_PROJECTS = CLAUDE_HOME / "projects"

SKILL_PATTERN = re.compile(r"(?:Skill tool|/)([a-z][a-z0-9-]+)", re.IGNORECASE)
MCP_PATTERN = re.compile(r"mcp__([a-z][a-z0-9_]+)__(?:[a-z_]+)", re.IGNORECASE)
MCP_SERVER_PATTERN = re.compile(r"mcp__([a-z][a-z0-9_]+)__", re.IGNORECASE)
MODEL_PATTERN = re.compile(
    r"\b(claude-[a-z0-9.-]+|glm-[a-z0-9.-]+|gpt-[0-9a-z.-]+|deepseek-[a-z0-9.-]+|qwen[0-9a-z.-]*)\b",
    re.IGNORECASE,
)
FIX_PATTERN = re.compile(
    r"(修复|解决|修了|fixed|solved|踩坑|bug|crash|崩溃|报错|error|失败|fallback|workaround)",
    re.IGNORECASE,
)
TURN_PATTERN = re.compile(r"\*\*老赫:\*\*|\*\*老茅:\*\*")


def load_registry() -> dict:
    """读 registry.json。容忍 JSON 解析错误（ProjectOS 写入时偶有转义 bug）"""
    if not REGISTRY_PATH.exists():
        return {}
    try:
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"[WARN] registry.json JSON 解析失败（继续无 registry 模式）: {e}", file=sys.stderr)
        return {}


def find_project_info(registry: dict, project_name: str) -> dict | None:
    """兼容 dict 格式（新）和 list 格式（旧）的 projects 字段"""
    projects = registry.get("projects", {})

    items: list[tuple[str, dict]] = []
    if isinstance(projects, dict):
        for key, p in projects.items():
            if isinstance(p, dict):
                items.append((key, p))
    elif isinstance(projects, list):
        for p in projects:
            if isinstance(p, dict):
                items.append(("", p))

    for key, p in items:
        name = p.get("name") or p.get("project_name")
        if name == project_name:
            return p
        path = p.get("project_path", "")
        if path and Path(path).name == project_name:
            return p
        if key == project_name:
            return p
    return None


def scan_conversation_log(project_path: Path) -> dict:
    log_file = project_path / "conversation_log.md"
    if not log_file.exists():
        return {
            "exists": False,
            "total_bytes": 0,
            "total_turns": 0,
            "days_count": 0,
            "skill_calls": {},
            "mcp_calls": {},
            "model_mentions": {},
            "fix_mentions_count": 0,
            "fix_mentions_sample": [],
        }

    content = log_file.read_text(encoding="utf-8", errors="ignore")

    skill_calls: dict[str, int] = {}
    for m in SKILL_PATTERN.finditer(content):
        name = m.group(1).lower()
        if name in {"and", "the", "for", "with", "http", "https"}:
            continue
        skill_calls[name] = skill_calls.get(name, 0) + 1

    mcp_calls: dict[str, int] = {}
    for m in MCP_PATTERN.finditer(content):
        key = m.group(0).lower()
        mcp_calls[key] = mcp_calls.get(key, 0) + 1

    mcp_servers: dict[str, int] = {}
    for m in MCP_SERVER_PATTERN.finditer(content):
        s = m.group(1).lower()
        mcp_servers[s] = mcp_servers.get(s, 0) + 1

    model_mentions: dict[str, int] = {}
    for m in MODEL_PATTERN.finditer(content):
        name = m.group(1).lower()
        model_mentions[name] = model_mentions.get(name, 0) + 1

    fix_mentions: list[str] = []
    for m in FIX_PATTERN.finditer(content):
        start = max(0, m.start() - 80)
        end = min(len(content), m.end() + 240)
        ctx = content[start:end]
        ctx = re.sub(r"\s+", " ", ctx).strip()
        if len(ctx) > 50:
            fix_mentions.append(ctx[:400])

    days_count = len(re.findall(r"^## \d{4}-\d{2}-\d{2}", content, re.MULTILINE))
    total_turns = len(TURN_PATTERN.findall(content))

    return {
        "exists": True,
        "total_bytes": len(content.encode("utf-8")),
        "total_turns": total_turns,
        "days_count": days_count,
        "skill_calls": skill_calls,
        "mcp_calls": mcp_calls,
        "mcp_servers": mcp_servers,
        "model_mentions": model_mentions,
        "fix_mentions_count": len(fix_mentions),
        "fix_mentions_sample": fix_mentions[:10],
    }


def encode_project_path(project_path: Path) -> str:
    """编码项目路径为 ~/.claude/projects/<encoded> 格式
    例：D:\\ClaudeCodeProjects\\hermes-desktop -> D--ClaudeCodeProjects-hermes-desktop
    """
    s = str(project_path)
    return s.replace(":", "-").replace("\\", "-").replace("/", "-")


def scan_project_memory(project_path: Path) -> dict:
    encoded = encode_project_path(project_path)
    memory_dir = CLAUDE_PROJECTS / encoded / "memory"

    if not memory_dir.exists():
        return {"exists": False, "memory_files": 0, "memory_types": {}, "memory_summaries": []}

    files = [f for f in memory_dir.glob("*.md") if f.name != "MEMORY.md"]
    types: dict[str, int] = {}
    summaries: list[dict] = []
    for f in files:
        text = f.read_text(encoding="utf-8", errors="ignore")
        type_m = re.search(r"^\s*type:\s*(\w+)", text, re.MULTILINE)
        name_m = re.search(r"^name:\s*([^\n]+)", text, re.MULTILINE)
        desc_m = re.search(r"^description:\s*([^\n]+)", text, re.MULTILINE)
        type_name = type_m.group(1).strip() if type_m else "unknown"
        types[type_name] = types.get(type_name, 0) + 1
        summaries.append({
            "file": f.name,
            "name": (name_m.group(1).strip() if name_m else ""),
            "description": (desc_m.group(1).strip() if desc_m else ""),
            "type": type_name,
        })

    return {
        "exists": True,
        "memory_dir": str(memory_dir),
        "memory_files": len(files),
        "memory_types": types,
        "memory_summaries": summaries,
    }


def scan_claude_md(project_path: Path) -> dict:
    claude_md = project_path / "CLAUDE.md"
    if not claude_md.exists():
        return {"has_claude_md": False, "char_count": 0, "constraints": []}

    text = claude_md.read_text(encoding="utf-8", errors="ignore")
    constraint_keywords = (
        "关键架构原则", "安全约束", "血泪硬约束", "硬约束", "踩坑", "约束",
        "关键约束", "不要踩坑", "TODO", "已修复", "关联",
    )
    constraints: list[str] = []
    pattern = re.compile(r"^(#+\s*.+)$", re.MULTILINE)
    headers = [m.group(1) for m in pattern.finditer(text)]
    sections: list[str] = []
    for kw in constraint_keywords:
        for h in headers:
            if kw in h:
                idx = text.find(h)
                if idx >= 0:
                    next_idx = len(text)
                    for next_h in headers:
                        nidx = text.find(next_h, idx + len(h))
                        if nidx > idx:
                            next_idx = min(next_idx, nidx)
                    section = text[idx:next_idx].strip()
                    clean = re.sub(r"\n+", "\n", section)
                    if len(clean) > 80:
                        sections.append(clean[:1500])
                    break
    constraints = sections[:6]

    return {
        "has_claude_md": True,
        "char_count": len(text),
        "constraints": constraints,
    }


def scan_git(project_path: Path) -> dict:
    if not (project_path / ".git").exists():
        return {"has_git": False}

    def _run(args: list[str]) -> str:
        try:
            r = subprocess.run(
                args,
                cwd=str(project_path),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=10,
            )
            return r.stdout or ""
        except Exception as e:
            return f"__ERROR__: {e}"

    commits_out = _run(["git", "log", "--since=14 days", "--pretty=%h %ad %s", "--date=short"])
    commits = [c for c in commits_out.strip().split("\n") if c and "__ERROR__" not in c]
    status_out = _run(["git", "status", "--porcelain"])
    uncommitted = [c for c in status_out.strip().split("\n") if c and "__ERROR__" not in c]
    branch_out = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).strip()

    return {
        "has_git": True,
        "branch": branch_out if "__ERROR__" not in branch_out else "",
        "commits_14d": len(commits),
        "recent_commits": commits[:15],
        "uncommitted_count": len(uncommitted),
    }


def scan_conversation_index(project_name: str) -> dict | None:
    if not CONVERSATION_INDEX.exists():
        return None
    try:
        data = json.loads(CONVERSATION_INDEX.read_text(encoding="utf-8"))
    except Exception:
        return None
    for p in data.get("projects", []):
        if p.get("project_name") == project_name:
            return {
                "last_updated": p.get("last_updated"),
                "total_turns": p.get("total_turns", 0),
                "total_bytes": p.get("total_bytes", 0),
                "first_seen": p.get("first_seen"),
            }
    return None


def scan_project(project_name: str, verbose: bool = True) -> dict | None:
    project_path = PROJECTS_ROOT / project_name
    if not project_path.exists():
        print(f"[ERROR] 项目不存在: {project_path}", file=sys.stderr)
        return None

    if verbose:
        print(f"[scanner] 扫描: {project_name} ({project_path})")

    registry = load_registry()
    project_info = find_project_info(registry, project_name)

    profile = {
        "project_name": project_name,
        "project_path": str(project_path),
        "scan_date": datetime.now().isoformat(timespec="seconds"),
        "scan_version": 1,
        "registry_info": project_info,
        "conversation_log": scan_conversation_log(project_path),
        "project_memory": scan_project_memory(project_path),
        "claude_md": scan_claude_md(project_path),
        "git": scan_git(project_path),
        "conversation_index": scan_conversation_index(project_name),
    }

    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    output_path = PROFILES_DIR / f"{project_name}.json"
    output_path.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if verbose:
        cl = profile["conversation_log"]
        pm = profile["project_memory"]
        g = profile["git"]
        print(f"  对话 log: {cl['total_bytes']} bytes / {cl['total_turns']} turns / {cl['days_count']} days")
        print(f"  Skill 调用种类: {len(cl['skill_calls'])}")
        print(f"  MCP 调用种类: {len(cl['mcp_calls'])}")
        print(f"  模型提及: {cl['model_mentions']}")
        print(f"  踩坑提及: {cl['fix_mentions_count']}")
        print(f"  项目记忆文件: {pm['memory_files']} ({pm['memory_types']})")
        print(f"  Git 近 14d 提交: {g.get('commits_14d', 0)} / 未提交: {g.get('uncommitted_count', 0)}")
        print(f"  行为画像: {output_path}")

    log_entry = (
        f"\n## {datetime.now().strftime('%Y-%m-%d %H:%M')} - scanner - {project_name}\n"
        f"- conversation_log: {profile['conversation_log']['total_bytes']} bytes / {profile['conversation_log']['total_turns']} turns\n"
        f"- Skill 调用种类: {len(profile['conversation_log']['skill_calls'])}\n"
        f"- MCP 调用种类: {len(profile['conversation_log']['mcp_calls'])}\n"
        f"- 模型提及: {profile['conversation_log']['model_mentions']}\n"
        f"- 踩坑提及次数: {profile['conversation_log']['fix_mentions_count']}\n"
        f"- 项目记忆文件数: {profile['project_memory']['memory_files']}\n"
        f"- Git 近 14d 提交: {profile['git'].get('commits_14d', 'N/A')}\n"
    )
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry)

    return profile


def main() -> int:
    parser = argparse.ArgumentParser(description="探路者：扫描项目 -> 行为画像")
    parser.add_argument("--project", help="项目名（如 hermes-desktop）")
    parser.add_argument("--all", action="store_true", help="扫所有 registry 项目")
    args = parser.parse_args()

    if args.all:
        registry = load_registry()
        projects = registry.get("projects", {})
        items: list[tuple[str, dict]] = []
        if isinstance(projects, dict):
            items = list(projects.items())
        elif isinstance(projects, list):
            items = [("", p) for p in projects if isinstance(p, dict)]
        count = 0
        for key, p in items:
            name = p.get("name") or p.get("project_name") or key
            if not name:
                continue
            try:
                if scan_project(name, verbose=False):
                    count += 1
            except Exception as e:
                print(f"[ERROR] {name}: {e}", file=sys.stderr)
        print(f"[scanner] 扫描完成: {count} 项目")
        return 0

    if not args.project:
        parser.print_help()
        return 1

    profile = scan_project(args.project)
    return 0 if profile else 1


if __name__ == "__main__":
    sys.exit(main())

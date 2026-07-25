"""
common.py - 共用工具：路径、LLM 调用、索引更新、日志

安全约束：
- LLM token 从 ~/.claude/settings.json 读，不打印不输出
- 任何错误信息禁止包含 token / API key
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROFILES_DIR = PROJECT_ROOT / "data" / "project_profiles"
LOG_FILE = PROJECT_ROOT / "data" / "evolution_log.md"
EXPERIENCE_DIR = PROJECT_ROOT / "experience"
INDEX_FILE = EXPERIENCE_DIR / "INDEX.md"

PROJECTS_ROOT = Path("D:/ClaudeCodeProjects")
CLAUDE_HOME = Path.home() / ".claude"
CLAUDE_PROJECTS = CLAUDE_HOME / "projects"
SETTINGS_PATH = CLAUDE_HOME / "settings.json"


def append_log(section: str, lines: list[str]) -> None:
    """追加到进化日志"""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    body = f"\n## {datetime.now().strftime('%Y-%m-%d %H:%M')} - {section}\n" + "\n".join(f"- {l}" for l in lines) + "\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(body)


def load_profile(project_name: str) -> dict | None:
    """读项目行为画像"""
    p = PROFILES_DIR / f"{project_name}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _load_settings_env() -> dict:
    """从 ~/.claude/settings.json 读 env 字段。
    禁止打印 token；只返回 Python 内部使用的 dict。
    """
    if not SETTINGS_PATH.exists():
        return {}
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        env = data.get("env", {}) if isinstance(data, dict) else {}
        return env if isinstance(env, dict) else {}
    except Exception as e:
        print(f"[WARN] settings.json 读取失败: {type(e).__name__}", file=sys.stderr)
        return {}


def call_llm(prompt: str, system: str | None = None, max_tokens: int = 4096, timeout: int = 120) -> dict:
    """调用 LLM via Anthropic 兼容协议（智谱 / 火山方舟代理）

    返回 dict: {
        "ok": bool,
        "text": str,           # LLM 输出文本
        "model": str,          # 实际使用的模型
        "error": str | None,
        "tokens_in": int,      # 输入 token
        "tokens_out": int,     # 输出 token
    }

    安全：token 仅在 Python 进程内传输，不打印不写日志。
    """
    env = _load_settings_env()
    base_url = env.get("ANTHROPIC_BASE_URL", "https://open.bigmodel.cn/api/anthropic").rstrip("/")
    token = env.get("ANTHROPIC_AUTH_TOKEN", "")
    model = env.get("ANTHROPIC_MODEL", "glm-5.2")

    if not token:
        # 只验证字段非空，不暴露值
        bool_token = bool(token)
        return {
            "ok": False,
            "text": "",
            "model": model,
            "error": f"ANTHROPIC_AUTH_TOKEN not configured (non-empty: {bool_token})",
            "tokens_in": 0,
            "tokens_out": 0,
        }

    messages = [{"role": "user", "content": prompt}]
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        payload["system"] = system

    url = f"{base_url}/v1/messages"
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("x-api-key", token)
    req.add_header("anthropic-version", "2023-06-01")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {
            "ok": False,
            "text": "",
            "model": model,
            "error": f"HTTP {e.code}: {e.reason}",
            "tokens_in": 0,
            "tokens_out": 0,
        }
    except Exception as e:
        return {
            "ok": False,
            "text": "",
            "model": model,
            "error": f"{type(e).__name__}: {e}",
            "tokens_in": 0,
            "tokens_out": 0,
        }

    content = result.get("content", [])
    text = "".join(block.get("text", "") for block in content if block.get("type") == "text")
    usage = result.get("usage", {})

    return {
        "ok": True,
        "text": text,
        "model": result.get("model", model),
        "error": None,
        "tokens_in": usage.get("input_tokens", 0),
        "tokens_out": usage.get("output_tokens", 0),
    }


def slugify(text: str, max_len: int = 60) -> str:
    """生成 slug"""
    s = re.sub(r"[^\w一-鿿-]", "-", text.strip()).strip("-").lower()
    return s[:max_len]


def update_index(category: str, slug: str, title: str, source_projects: list[str]) -> None:
    """在 experience/INDEX.md 追加经验条目索引"""
    if not INDEX_FILE.exists():
        INDEX_FILE.write_text("# 虚空藏经阁 - 经验库索引\n", encoding="utf-8")

    text = INDEX_FILE.read_text(encoding="utf-8")
    # 清理"暂无条目"占位符
    text = re.sub(r"\*暂无条目[^*]*\*", "", text)
    line = f"- [{title}]({category}/{slug}.md) (来源: {', '.join(source_projects)})"
    anchor = "<!-- EXTRACTOR_APPEND_BELOW_THIS_LINE -->"
    if anchor not in text:
        text += "\n\n" + anchor + "\n" + line + "\n"
    else:
        text = text.replace(anchor, anchor + "\n" + line, 1)
    INDEX_FILE.write_text(text, encoding="utf-8")


def write_experience(
    category: str,
    slug: str,
    title: str,
    source_projects: list[str],
    body: str,
    applicable_when: str = "",
    not_applicable_when: str = "",
    tags: list[str] | None = None,
    token_saved_estimate: int = 0,
) -> Path:
    """写一条经验到 experience/<category>/<slug>.md"""
    cat_dir = EXPERIENCE_DIR / category
    cat_dir.mkdir(parents=True, exist_ok=True)
    path = cat_dir / f"{slug}.md"

    frontmatter = [
        "---",
        f"title: {title}",
        f"category: {category}",
        f"source_projects: [{', '.join(source_projects)}]",
        f"created: {datetime.now().strftime('%Y-%m-%d')}",
        f"applicable_when: {applicable_when}",
        f"not_applicable_when: {not_applicable_when}",
        f"token_saved_estimate: {token_saved_estimate}",
    ]
    if tags:
        frontmatter.append(f"tags: [{', '.join(tags)}]")
    frontmatter.append("---")
    frontmatter.append("")

    path.write_text("\n".join(frontmatter) + "\n" + body + "\n", encoding="utf-8")
    return path


def ensure_memory_indexed(
    memory_dir: Path,
    file_name: str,
    title: str,
    description: str,
) -> None:
    """维护项目级 MEMORY.md 索引（幂等）
    如果对应条目已存在，更新；不存在，追加。
    """
    memory_dir.mkdir(parents=True, exist_ok=True)
    memory_index = memory_dir / "MEMORY.md"
    if not memory_index.exists():
        memory_index.write_text(
            "# Project Memory Index\n\nAuto-maintained by ai-self-evolution injector + Claude sessions.\n",
            encoding="utf-8",
        )

    text = memory_index.read_text(encoding="utf-8")
    # 检查是否已存在（按 file_name 匹配）
    pattern = re.compile(r"^- \[[^\]]+\]\(" + re.escape(file_name) + r"\) .*$", re.MULTILINE)
    new_line = f"- [{title}]({file_name}) - {description}"

    if pattern.search(text):
        # 更新
        text = pattern.sub(new_line, text)
    else:
        # 追加（确保末尾有换行）
        if not text.endswith("\n"):
            text += "\n"
        text += new_line + "\n"

    memory_index.write_text(text, encoding="utf-8")

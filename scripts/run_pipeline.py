"""
run_pipeline.py - 一键跑 scanner -> extractor -> injector

用法：
    python scripts/run_pipeline.py --project hermes-desktop
    python scripts/run_pipeline.py --project hermes-desktop --skip-llm   # 只扫+注入（不调 LLM 提炼）
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 把项目根加入 sys.path，让 agents 包可 import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents import common
from agents import scanner as scanner_mod
from agents import extractor as extractor_mod
from agents import injector as injector_mod


def run_pipeline(project_name: str, skip_llm: bool = False, skip_inject: bool = False, verbose: bool = True) -> bool:
    """跑全流程。返回是否成功"""
    print(f"\n{'=' * 60}")
    print(f"  虚空藏经阁 Pipeline - {project_name}")
    print(f"{'=' * 60}\n")

    # 1. scanner
    print("[1/3] scanner (探路者) ...")
    profile = scanner_mod.scan_project(project_name, verbose=verbose)
    if not profile:
        return False
    print()

    # 2. extractor
    if skip_llm:
        print("[2/3] extractor (炼金师) - SKIPPED (--skip-llm)")
    else:
        print("[2/3] extractor (炼金师) - 调 LLM 提炼经验 ...")
        written = extractor_mod.extract(project_name, verbose=verbose)
        if not written and not _confirm_continue("提取 0 条经验，是否继续注入？"):
            return False
    print()

    # 3. injector
    if skip_inject:
        print("[3/3] injector (分院帽) - SKIPPED")
    else:
        print("[3/3] injector (分院帽) - 注入项目记忆 ...")
        result = injector_mod.inject(project_name, verbose=verbose)
        if not result:
            print("[WARN] 注入未完成", file=sys.stderr)
    print()

    print(f"{'=' * 60}")
    print(f"  ✓ Pipeline 完成: {project_name}")
    print(f"{'=' * 60}")
    print(f"\n下一步：")
    print(f"  - 查看行为画像: data/project_profiles/{project_name}.json")
    print(f"  - 查看经验库:   experience/INDEX.md")
    print(f"  - 查看注入结果: ~/.claude/projects/D--ClaudeCodeProjects-{project_name}/memory/cross-project-experience.md")
    print(f"  - 查看进化日志: data/evolution_log.md")

    common.append_log(f"pipeline - {project_name} (完成)", [
        f"skip_llm: {skip_llm}",
        f"skip_inject: {skip_inject}",
    ])
    return True


def _confirm_continue(msg: str) -> bool:
    """非交互模式默认继续"""
    print(f"  [INFO] {msg} (非交互模式，继续)")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="虚空藏经阁一键 pipeline")
    parser.add_argument("--project", required=True, help="项目名（如 hermes-desktop）")
    parser.add_argument("--skip-llm", action="store_true", help="跳过 extractor LLM 调用")
    parser.add_argument("--skip-inject", action="store_true", help="跳过 injector 注入")
    args = parser.parse_args()

    ok = run_pipeline(
        args.project,
        skip_llm=args.skip_llm,
        skip_inject=args.skip_inject,
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

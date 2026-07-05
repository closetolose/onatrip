#!/usr/bin/env python3
"""
UI frontend workflow via Cursor SDK API.

Pipeline: Critic → Planner → Implementer → Reviewer (loop on NEEDS_FIX).

Requires:
  pip install cursor-sdk
  set CURSOR_API_KEY=...   (Cursor Dashboard → API Keys)

Example:
  python scripts/ui_frontend_workflow.py
  python scripts/ui_frontend_workflow.py --page http://127.0.0.1:8765/days/12.html?k=trip2026live
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS_DIR = REPO_ROOT / ".cursor" / "agents"
RUNS_DIR = REPO_ROOT / ".cursor" / "ui-workflow-runs"

AGENT_FILES = {
    "ui-critic": "ui-critic.md",
    "ui-planner": "ui-planner.md",
    "ui-implementer": "ui-implementer.md",
    "ui-reviewer": "ui-reviewer.md",
}


def parse_agent_md(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n(.*)$", text, re.DOTALL)
    if not match:
        raise ValueError(f"Invalid agent frontmatter: {path}")

    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip().strip('"').strip("'")

    return meta, match.group(2).strip()


def load_agent(name: str) -> tuple[str, str]:
    filename = AGENT_FILES.get(name)
    if not filename:
        raise KeyError(f"Unknown agent: {name}")
    path = AGENTS_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"Agent file not found: {path}")
    meta, body = parse_agent_md(path)
    description = meta.get("description", name)
    prompt = body
    if meta.get("readonly", "").lower() == "true":
        prompt = (
            "READONLY MODE: do not edit files or run state-changing shell commands.\n\n"
            + prompt
        )
    return description, prompt


def ensure_sdk():
    try:
        from cursor_sdk import Agent, AgentDefinition, LocalAgentOptions  # noqa: F401
    except ImportError as exc:
        print(
            "cursor-sdk is not installed.\n"
            "  pip install cursor-sdk\n"
            "  set CURSOR_API_KEY=your_key",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc


def run_subagent(
    name: str,
    user_message: str,
    *,
    model: str,
    api_key: str | None,
    cwd: Path,
) -> str:
    from cursor_sdk import Agent, AgentDefinition, LocalAgentOptions

    description, prompt = load_agent(name)
    invoke = (
        f"You are the `{name}` subagent. Follow your system instructions exactly.\n\n"
        f"{user_message}"
    )

    with Agent.create(
        model=model,
        api_key=api_key,
        local=LocalAgentOptions(cwd=str(cwd)),
        agents={
            name: AgentDefinition(
                description=description,
                prompt=prompt,
                model="inherit",
            ),
        },
    ) as agent:
        run = agent.send(invoke)
        run.wait()
        return run.text()


def write_artifact(run_dir: Path, filename: str, content: str) -> Path:
    path = run_dir / filename
    path.write_text(content, encoding="utf-8")
    print(f"  saved {path.relative_to(REPO_ROOT)}")
    return path


def parse_review_status(review: str) -> str:
    for line in review.splitlines():
        stripped = line.strip()
        if stripped.startswith("STATUS:"):
            return stripped.split(":", 1)[1].strip().upper()
    upper = review.upper()
    if "STATUS: APPROVED" in upper:
        return "APPROVED"
    if "STATUS: NEEDS_FIX" in upper:
        return "NEEDS_FIX"
    return "NEEDS_FIX"


def main() -> int:
    parser = argparse.ArgumentParser(description="UI workflow: Critic → Planner → Implementer ↔ Reviewer")
    parser.add_argument(
        "--page",
        default="http://127.0.0.1:8765/index.html?k=trip2026live",
        help="URL to review (for critic prompt)",
    )
    parser.add_argument(
        "--scope",
        default=(
            "live_plan/assets/style.css, live_plan/template.html, "
            "live_plan/day_template.html, live_plan/assets/map.js, live_plan/assets/app.js"
        ),
        help="Files in scope for fixes",
    )
    parser.add_argument(
        "--max-review-rounds",
        type=int,
        default=3,
        help="Max implementer↔reviewer loops",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("CURSOR_MODEL", "composer-2.5"),
        help="Cursor model id",
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=None,
        help="Directory for artifacts (default: .cursor/ui-workflow-runs/<timestamp>)",
    )
    args = parser.parse_args()

    ensure_sdk()
    api_key = os.environ.get("CURSOR_API_KEY")
    if not api_key:
        print("Warning: CURSOR_API_KEY is not set.", file=sys.stderr)

    run_dir = args.run_dir or RUNS_DIR / datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "page": args.page,
        "scope": args.scope,
        "model": args.model,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    write_artifact(run_dir, "00-meta.json", __import__("json").dumps(meta, ensure_ascii=False, indent=2))

    print("\n[1/4] ui-critic")
    critic_report = run_subagent(
        "ui-critic",
        f"Review this page and related templates:\n\n"
        f"- URL: {args.page}\n"
        f"- Scope files: {args.scope}\n\n"
        f"Return the critic report in the required markdown format.",
        model=args.model,
        api_key=api_key,
        cwd=REPO_ROOT,
    )
    write_artifact(run_dir, "01-critic.md", critic_report)

    print("\n[2/4] ui-planner")
    plan = run_subagent(
        "ui-planner",
        f"Critic report:\n\n{critic_report}\n\n"
        f"Create a fix plan for scope: {args.scope}",
        model=args.model,
        api_key=api_key,
        cwd=REPO_ROOT,
    )
    write_artifact(run_dir, "02-planner.md", plan)

    reviewer_feedback = ""
    final_status = "NEEDS_FIX"
    rounds_used = 0

    for round_num in range(1, args.max_review_rounds + 1):
        rounds_used = round_num
        print(f"\n[3/4] ui-implementer (round {round_num})")
        impl_prompt = f"Fix plan:\n\n{plan}\n\nScope: {args.scope}\n\nAfter edits run: python build_live_plan.py"
        if reviewer_feedback:
            impl_prompt += f"\n\nReviewer feedback to address:\n\n{reviewer_feedback}"

        implementer_report = run_subagent(
            "ui-implementer",
            impl_prompt,
            model=args.model,
            api_key=api_key,
            cwd=REPO_ROOT,
        )
        write_artifact(run_dir, f"03-implementer-r{round_num}.md", implementer_report)

        print(f"\n[4/4] ui-reviewer (round {round_num})")
        review = run_subagent(
            "ui-reviewer",
            f"Fix plan:\n\n{plan}\n\nImplementer report:\n\n{implementer_report}\n\n"
            f"Review git diff in live_plan/ and rebuilt docs/. "
            f"Respond with STATUS: APPROVED or STATUS: NEEDS_FIX.",
            model=args.model,
            api_key=api_key,
            cwd=REPO_ROOT,
        )
        write_artifact(run_dir, f"04-reviewer-r{round_num}.md", review)

        final_status = parse_review_status(review)
        if final_status == "APPROVED":
            print(f"\nWorkflow finished: APPROVED after {round_num} round(s).")
            break
        reviewer_feedback = review
        print(f"  reviewer returned NEEDS_FIX — sending back to implementer")
    else:
        print(f"\nWorkflow stopped: max review rounds ({args.max_review_rounds}) reached.")

    summary = (
        f"# UI workflow summary\n\n"
        f"- Status: **{final_status}**\n"
        f"- Review rounds: {rounds_used}\n"
        f"- Page: {args.page}\n"
        f"- Artifacts: `{run_dir.relative_to(REPO_ROOT)}`\n"
    )
    write_artifact(run_dir, "05-summary.md", summary)
    print(f"\nArtifacts: {run_dir}")
    return 0 if final_status == "APPROVED" else 1


if __name__ == "__main__":
    raise SystemExit(main())

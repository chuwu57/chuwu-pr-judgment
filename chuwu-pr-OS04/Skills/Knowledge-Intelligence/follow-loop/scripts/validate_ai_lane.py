#!/usr/bin/env python3
"""Validate the Follow Loop AI-person lane and its shared checkpoints."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

STATE = Path("Domains/PR/90-System/Follow-Loop/State.md")
SKILL = Path("Skills/Knowledge-Intelligence/follow-loop")
AI_FIELDS = (
    "x_scanned_through",
    "x_last_content_published_at",
    "x_last_content_id",
    "x_feed_commit",
    "podcast_scanned_through",
    "podcast_last_content_published_at",
    "podcast_last_content_id",
    "podcast_feed_commit",
)
PROCESS_PHRASES = ("本轮", "本次扫描", "此次抓取", "Feed超时", "检查点冻结", "断点冻结")
RELATIONS = {"新分支", "强化", "细化", "修正", "反转", "从观点到行动", "当前信号"}
CONTENT_TYPES = {"观点", "行动", "信息"}


def normalized_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = [(key, value) for key, value in parse_qsl(parts.query) if not key.lower().startswith("utm_")]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), urlencode(query), ""))


def validate_person_assets(root: Path) -> list[str]:
    errors: list[str] = []
    profiles = root / "Domains/AI/Builders"
    evidence_root = root / "Domains/PR/60-References/Evidence/AI-Builders"
    for profile in sorted(profiles.glob("*.md")):
        if profile.name == "README.md":
            continue
        evidence = evidence_root / f"{profile.stem}-Evidence.md"
        if not evidence.exists():
            errors.append(f"AI人物缺少Evidence：{profile.stem}")
            continue
        profile_text = profile.read_text(encoding="utf-8")
        evidence_text = evidence.read_text(encoding="utf-8")
        for heading in ("## 人物定位", "## 当前坐标", "## 更新记录", "## 思维发展主线", "## 判断边界"):
            if heading not in profile_text:
                errors.append(f"AI人物缺少结构：{profile.name} {heading}")
        for phrase in PROCESS_PHRASES:
            if phrase in profile_text or phrase in evidence_text:
                errors.append(f"AI长期资产混入运行措辞：{profile.stem} {phrase}")
        update_section = profile_text.split("## 更新记录", 1)[-1].split("\n## ", 1)[0]
        for line in update_section.splitlines():
            if not re.match(r"^\| \d{4}-\d{2}-\d{2} \|", line):
                continue
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) != 5 or cells[2] not in CONTENT_TYPES or cells[3] not in RELATIONS:
                errors.append(f"AI更新记录枚举非法：{profile.name} {line}")
            if not re.search(r"\[原文\]\(https?://", cells[-1]):
                errors.append(f"AI更新记录未直链原文：{profile.name} {line}")
        urls = [normalized_url(url) for url in re.findall(r"^- 原始链接：\s*(https?://\S+)", evidence_text, re.M)]
        if not urls:
            errors.append(f"AI Evidence没有原始链接：{evidence.name}")
        if len(urls) != len(set(urls)):
            errors.append(f"AI Evidence存在规范化重复URL：{evidence.name}")
        if not frontmatter(evidence).get("last_reviewed"):
            errors.append(f"AI Evidence缺少顶层last_reviewed：{evidence.name}")
        entries = re.findall(r"^## (.+?)\n(.*?)(?=^## |\Z)", evidence_text, re.M | re.S)
        for title, body in entries:
            if "- 支持的判断：" in body and "- 边界或疑点：" not in body:
                errors.append(f"AI Evidence条目缺少边界或疑点：{evidence.name} {title}")
    return errors


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    if not match:
        return {}
    values: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip().strip('"\'')
    return values


def validate(root: Path, baseline: Path | None, manifest: Path | None) -> list[str]:
    errors: list[str] = []
    skill_dir = root / SKILL
    state_path = root / STATE
    required = [
        skill_dir / "SKILL.md",
        skill_dir / "agents/openai.yaml",
        skill_dir / "references/ai-knowledge-contract.md",
        skill_dir / "references/ai-person-evolution-model.md",
        state_path,
        root / "Domains/AI/Builders",
        root / "Domains/PR/60-References/Evidence/AI-Builders",
    ]
    for path in required:
        if not path.exists():
            errors.append(f"缺少AI lane资产：{path.relative_to(root)}")

    if not errors:
        skill_text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        prompt = (skill_dir / "agents/openai.yaml").read_text(encoding="utf-8")
        if "name: follow-loop" not in skill_text or "$follow-loop" not in prompt:
            errors.append("AI lane未绑定follow-loop Skill")
        state = frontmatter(state_path)
        if state.get("skill") != "follow-loop":
            errors.append("统一State.md的skill必须是follow-loop")
        for field in AI_FIELDS:
            if not state.get(field):
                errors.append(f"统一State.md缺少AI断点：{field}")
        body = state_path.read_text(encoding="utf-8")
        for source_id in ("ai-builder-x-feed", "ai-builder-podcast-feed"):
            if f"| {source_id} | deterministic |" not in body:
                errors.append(f"统一State.md缺少AI来源行：{source_id}")

    errors.extend(validate_person_assets(root))

    if bool(baseline) != bool(manifest):
        errors.append('--baseline-state与--run-manifest必须成对提供')
    elif baseline and manifest:
        from validate_follow_loop import validate_manifest
        errors.extend(validate_manifest(root, baseline, manifest))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[4]))
    parser.add_argument("--baseline-state", type=Path)
    parser.add_argument("--run-manifest", type=Path)
    args = parser.parse_args()
    if bool(args.baseline_state) != bool(args.run_manifest):
        parser.error("--baseline-state与--run-manifest必须成对提供")
    root = Path(args.root).resolve()
    errors = validate(root, args.baseline_state, args.run_manifest)
    if errors:
        print("FAIL: Follow Loop AI lane")
        for error in errors:
            print(f"- {error}")
        return 1
    print("PASS: Follow Loop AI lane")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate the Follow Loop PR-person and signal lanes."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

SYSTEM = Path("Domains/PR/90-System/Follow-Loop")
SKILL = Path("Skills/Knowledge-Intelligence/follow-loop")
PROCESS_PHRASES = ("本轮", "本次扫描", "此次抓取", "RSS超时", "检查点冻结", "断点冻结")
RELATIONS = {"新分支", "强化", "细化", "修正", "反转", "从观点到行动", "当前信号"}
CONTENT_TYPES = {"观点", "行动", "信息"}


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    if not match:
        return {}
    values: dict[str, object] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        raw = value.strip().strip('"\'')
        values[key.strip()] = int(raw) if raw.isdigit() else raw
    return values


def validate_signal_stages(text: str) -> list[str]:
    """Check declared minimum evidence counts; independence still needs source review."""
    errors = []
    stages = {"单点信号", "交叉信号", "形成中趋势", "稳定趋势", "降温", "失效"}
    for block in re.split(r"(?m)^### ", text)[1:]:
        title = block.splitlines()[0]
        fields = dict(re.findall(r"(?m)^- ([^：\n]+)：([^\n]*)$", block))
        stage = fields.get("信号阶段")
        if stage not in stages:
            errors.append(f"PR信号阶段非法：{title}")
            continue
        subjects = {v.strip() for v in fields.get("独立主体", "").split("；") if v.strip()}
        kinds = {v.strip() for v in fields.get("来源类型", "").split("；") if v.strip()}
        if stage == "交叉信号" and len(subjects) < 2:
            errors.append(f"交叉信号缺少两个已声明独立主体：{title}")
        if stage in {"形成中趋势", "稳定趋势"}:
            if len(subjects) < 3 or len(kinds) < 2:
                errors.append(f"趋势升级未达到三主体／两类来源：{title}")
            if not re.search(r"https?://", fields.get("行动／案例／研究证据", "")):
                errors.append(f"趋势缺少行动／案例／研究原文链接：{title}")
        if stage == "稳定趋势":
            cycles = fields.get("成功扫描周期", "")
            if not cycles.isdigit() or int(cycles) < 2:
                errors.append(f"稳定趋势缺少两个成功扫描周期：{title}")
    return errors


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    paths = [
        root / SYSTEM / "Sources.yml",
        root / SYSTEM / "Topics.yml",
        root / SYSTEM / "State.md",
        root / SKILL / "references/pr-knowledge-contract.md",
        root / SKILL / "references/pr-person-evolution-model.md",
        root / SKILL / "references/pr-trend-model.md",
        root / "Domains/PR/10-Thinking/PR-Builders/PR-Signal-Radar.md",
        root / "Domains/PR/60-References/Evidence/PR-Builders",
    ]
    for path in paths:
        if not path.exists():
            errors.append(f"缺少PR lane资产：{path.relative_to(root)}")
    if errors:
        return errors

    source_text = (root / SYSTEM / "Sources.yml").read_text(encoding="utf-8")
    source_section = source_text.split("\nsources:\n", 1)[-1]
    blocks = re.findall(r"(?ms)^  - id: .*?(?=^  - id: |\Z)", source_section)
    ids = [re.search(r"^  - id: ([^\n]+)", block).group(1).strip() for block in blocks]
    if not ids or len(ids) != len(set(ids)):
        errors.append("Sources.yml来源id缺失或重复")
    for source_id, block in zip(ids, blocks):
        if "active: true" in block and not re.search(r"coverage_mode: (deterministic|best_effort)", block):
            errors.append(f"来源coverage_mode非法：{source_id}")

    topic_text = (root / SYSTEM / "Topics.yml").read_text(encoding="utf-8")
    topic_ids = set(re.findall(r"^      - id: ([^\n]+)$", topic_text, re.M))
    required_topics = {
        "ai-builder-intelligence",
        "ai-communication",
        "embodied-intelligence-communication",
        "luxury-intelligence",
        "consumer-products-communication",
        "general-pr-practice",
        "case-follow-discovery",
    }
    if not required_topics.issubset(topic_ids):
        errors.append(f"Topics.yml缺少主题：{sorted(required_topics - topic_ids)}")

    state = frontmatter(root / SYSTEM / "State.md")
    if state.get("skill") != "follow-loop" or state.get("overlap_hours") != 48:
        errors.append("统一State.md必须绑定follow-loop并保留48小时重叠窗口")

    registry_text = (root / "Skills/registry.yml").read_text(encoding="utf-8")
    if not re.search(r"^  follow-loop:\n    path: Skills/Knowledge-Intelligence/follow-loop$", registry_text, re.M):
        errors.append("Skills/registry.yml未正确注册follow-loop")
    for obsolete in ("ai-builders-follow", "pr-builders-follow"):
        if re.search(rf"^  {re.escape(obsolete)}:", registry_text, re.M):
            errors.append(f"Skills/registry.yml仍含旧Skill：{obsolete}")

    people_root = root / "Domains/PR/10-Thinking/PR-Builders/People"
    evidence_root = root / "Domains/PR/60-References/Evidence/PR-Builders/People"
    for profile in sorted(people_root.glob("*.md")):
        evidence = evidence_root / f"{profile.stem}-Evidence.md"
        if not evidence.exists():
            errors.append(f"PR人物缺少Evidence：{profile.stem}")
            continue
        profile_text = profile.read_text(encoding="utf-8")
        evidence_text = evidence.read_text(encoding="utf-8")
        for heading in ("## 人物定位", "## 当前坐标", "## 更新记录", "## 思维发展主线", "## 判断边界"):
            if heading not in profile_text:
                errors.append(f"PR人物缺少结构：{profile.name} {heading}")
        for phrase in PROCESS_PHRASES:
            if phrase in profile_text or phrase in evidence_text:
                errors.append(f"PR长期资产混入运行措辞：{profile.stem} {phrase}")
        update_section = profile_text.split("## 更新记录", 1)[-1].split("\n## ", 1)[0]
        for line in update_section.splitlines():
            if not re.match(r"^\| \d{4}-\d{2}-\d{2} \|", line):
                continue
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) != 5 or cells[2] not in CONTENT_TYPES or cells[3] not in RELATIONS:
                errors.append(f"PR更新记录枚举非法：{profile.name} {line}")
            if not re.search(r"\[原文\]\(https?://", cells[-1]):
                errors.append(f"PR更新记录未直链原文：{profile.name} {line}")
    errors.extend(validate_signal_stages((root / "Domains/PR/10-Thinking/PR-Builders/PR-Signal-Radar.md").read_text(encoding="utf-8")))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[4]))
    args = parser.parse_args()
    errors = validate(Path(args.root).resolve())
    if errors:
        print("FAIL: Follow Loop PR lane")
        for error in errors:
            print(f"- {error}")
        return 1
    print("PASS: Follow Loop PR lane")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate Follow Loop Embodied Follow assets."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


SKILL = Path("Skills/Knowledge-Intelligence/follow-loop")
ASSET_ROOT = Path("Domains/AI/Embodied-Intelligence")
EVIDENCE_ROOT = Path("Domains/PR/60-References/Evidence/Embodied-Intelligence")
RELATIONS = {"新分支", "强化", "细化", "修正", "反转", "从观点到行动", "当前信号"}
CONTENT_TYPES = {"研究", "产品", "部署", "组织", "信息"}
PROCESS_PHRASES = ("本轮", "本次扫描", "此次抓取", "检查点冻结", "断点冻结")


def normalized_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = [(key, value) for key, value in parse_qsl(parts.query) if not key.lower().startswith("utm_")]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), urlencode(query), ""))


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    required = [
        root / SKILL / "references/embodied-intelligence-model.md",
        root / ASSET_ROOT / "README.md",
        root / ASSET_ROOT / "Embodied-Intelligence-Signal-Radar.md",
        root / ASSET_ROOT / "Entities",
        root / EVIDENCE_ROOT,
    ]
    for path in required:
        if not path.exists():
            errors.append(f"缺少Embodied Follow资产：{path.relative_to(root)}")
    if errors:
        return errors

    profiles = sorted((root / ASSET_ROOT / "Entities").glob("*.md"))
    if not profiles:
        errors.append("Embodied Follow没有对象档案")
    for profile in profiles:
        evidence = root / EVIDENCE_ROOT / f"{profile.stem}-Evidence.md"
        if not evidence.exists():
            errors.append(f"具身智能对象缺少Evidence：{profile.stem}")
            continue
        profile_text = profile.read_text(encoding="utf-8")
        evidence_text = evidence.read_text(encoding="utf-8")
        for heading in ("## 对象定位", "## 当前坐标", "## 更新记录", "## 演化主线", "## 证据边界"):
            if heading not in profile_text:
                errors.append(f"具身智能对象缺少结构：{profile.name} {heading}")
        for phrase in PROCESS_PHRASES:
            if phrase in profile_text or phrase in evidence_text:
                errors.append(f"具身智能长期资产混入运行措辞：{profile.stem} {phrase}")
        section = profile_text.split("## 更新记录", 1)[-1].split("\n## ", 1)[0]
        for line in section.splitlines():
            if not re.match(r"^\| \d{4}-\d{2}-\d{2} \|", line):
                continue
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) != 5 or cells[2] not in CONTENT_TYPES or cells[3] not in RELATIONS:
                errors.append(f"具身智能更新记录枚举非法：{profile.name} {line}")
            if not re.search(r"\[原文\]\(https?://", cells[-1]):
                errors.append(f"具身智能更新记录未直链原文：{profile.name} {line}")
        urls = [normalized_url(url) for url in re.findall(r"^- 原始链接：\s*(https?://\S+)", evidence_text, re.M)]
        if not urls:
            errors.append(f"具身智能Evidence没有原始链接：{evidence.name}")
        if len(urls) != len(set(urls)):
            errors.append(f"具身智能Evidence存在规范化重复URL：{evidence.name}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[4]))
    args = parser.parse_args()
    errors = validate(Path(args.root).resolve())
    if errors:
        print("FAIL: Follow Loop Embodied Follow")
        for error in errors:
            print(f"- {error}")
        return 1
    print("PASS: Follow Loop Embodied Follow")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

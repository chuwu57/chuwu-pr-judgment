#!/usr/bin/env python3
"""Lexical signal collection only; no risk score or publication decision."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


RULES = (
    ('relationship_language', r'老公|老婆|婚纱|出轨|情人|小三', 'references/perspective-library.md'),
    ('family_language', r'妈妈|母亲|爸爸|父亲|孩子|家庭|夫妻', 'references/perspective-library.md'),
    ('identity_language', r'女性|女人|贤惠|身材|残疾|贫困|低学历|老年', 'references/perspective-library.md'),
    ('fandom_language', r'本命|饭圈|追星|爱豆|塌房|应援', 'references/perspective-library.md'),
    ('judgmental_language', r'不配|拖后腿|没文化|低端|毒粮', 'SKILL.md'),
    ('health_or_absolute_claim', r'治愈|治疗|预防.{0,8}疾病|替代兽医|替代药物|100[%％]|百分之百|绝对安全|\d+天.{0,6}见效', 'references/pet-food-runtime.md'),
)


def review(raw: dict) -> dict:
    copy = raw.get('copy', '')
    if not isinstance(copy, str) or not copy.strip():
        raise ValueError('copy must be a non-empty string')
    signals = []
    for category, pattern, reference in RULES:
        for match in re.finditer(pattern, copy):
            signals.append({
                'category': category,
                'matched_text': match.group(),
                'source_field': 'copy',
                'span': [match.start(), match.end()],
                'rule_reference': reference,
            })
    return {
        'assessment_status': 'signals_only',
        'copy': copy,
        'signals': signals,
        'interpretation': '词语命中仅用于定位复核；身份、家庭或健康词本身不证明冒犯或虚假，未命中也不代表安全。',
        'unreviewed_dimensions': [
            '实际创意意图、完整图文和截图语义',
            '事实、标签、功效及承诺的证据',
            '行业与当前法律要求的适用性',
            '受众伤害、组织承接能力与实际发布授权',
        ],
    }


def render_markdown(result: dict) -> str:
    signals = '\n'.join(
        f'- {item["category"]}：{item["matched_text"]!r}；copy[{item["span"][0]}:{item["span"][1]}]；参考{item["rule_reference"]}'
        for item in result['signals']
    ) or '- 未命中当前词表；仍需结合语境与证据审查。'
    unreviewed = '\n'.join('- ' + item for item in result['unreviewed_dimensions'])
    return f'# 文案信号初筛\n\n状态：signals_only\n\n{result["interpretation"]}\n\n## 原文\n\n{result["copy"]}\n\n## 原文命中\n\n{signals}\n\n## 尚未完成的审查\n\n{unreviewed}\n'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input_json', type=Path)
    parser.add_argument('--format', choices=['json', 'markdown'], default='markdown')
    args = parser.parse_args()
    try:
        raw = json.loads(args.input_json.read_text(encoding='utf-8'))
        if not isinstance(raw, dict):
            raise ValueError('input must be a JSON object')
        result = review(raw)
    except (OSError, ValueError) as exc:
        parser.exit(2, f'Input error: {exc}\n')
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.format == 'json' else render_markdown(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

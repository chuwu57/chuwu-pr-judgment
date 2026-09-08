#!/usr/bin/env python3
"""Check a Markdown report against its selected scope, not research truth."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


MODULES = {
    'executive_summary': ('执行摘要', '核心结论'),
    'scope': ('研究边界', '行业边界', '口径'),
    'history_forecast': ('历史', '预测', '情景'),
    'customers': ('客户', '消费者', '采用', '需求'),
    'economics': ('利润池', '单位经济', '完全成本'),
    'competition': ('竞争', '公司质量', '公司图谱'),
    'technology': ('技术', '工艺', '成本曲线'),
    'go_to_market': ('GTM', '渠道', '媒介', '达人'),
    'region_policy': ('区域', '政策', '合规', '出海'),
    'monitoring': ('动态监测', '领先指标', '触发动作'),
    'limitations': ('尚不能回答', '限制', '剩余边界', '证据缺口'),
    'priority_status': ('P0', 'P1'),
}
QUICK_MODULES = ('executive_summary', 'scope', 'limitations', 'priority_status')


def resolve_scope(mode: str | None, contract: dict) -> tuple[str, list[str]]:
    contract_mode = contract.get('mode')
    if mode and contract_mode and mode != contract_mode:
        raise ValueError('--mode conflicts with contract.mode')
    mode = mode or contract_mode or 'standard'
    if mode not in ('quick', 'standard', 'deep'):
        raise ValueError('mode must be quick, standard or deep')
    required = contract.get('required_modules')
    excluded = contract.get('excluded_modules', [])
    if excluded is None:
        raise ValueError('excluded_modules must be a list, not null')
    for name, values in (('required_modules', required), ('excluded_modules', excluded)):
        if values is not None and (not isinstance(values, list) or any(not isinstance(v, str) or v not in MODULES for v in values)):
            raise ValueError(f'{name} must list known module IDs: {", ".join(MODULES)}')
    if required is not None and set(required) & set(excluded):
        raise ValueError('required_modules and excluded_modules overlap')
    selected = list(required) if required is not None else list(QUICK_MODULES if mode == 'quick' else MODULES)
    return mode, list(dict.fromkeys(name for name in selected if name not in excluded))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--mode', choices=['quick', 'standard', 'deep'])
    parser.add_argument('--contract', type=Path, help='JSON with mode, required_modules and/or excluded_modules')
    args = parser.parse_args()
    try:
        contract = json.loads(args.contract.read_text(encoding='utf-8')) if args.contract else {}
        if not isinstance(contract, dict):
            raise ValueError('contract must be a JSON object')
        mode, required = resolve_scope(args.mode, contract)
        text = args.report.read_text(encoding='utf-8')
    except (OSError, ValueError) as exc:
        parser.exit(2, f'Input error: {exc}\n')

    failures, warnings = [], []
    for group in required:
        if not any(term.casefold() in text.casefold() for term in MODULES[group]):
            failures.append(f'missing_module: {group}; check scope or add the required content')
    if not text.strip():
        failures.append('empty_report')
    if re.search(r'^\s*(?:TODO|TBD|这里填写|\[链接\])\s*$', text, re.M):
        failures.append('unfinished_scaffold: replace an empty scaffold with content or an explicit evidence gap')
    urls = re.findall(r'https?://[^\s)>]+', text)
    unique_urls = set(urls)
    if len(unique_urls) < len(urls):
        warnings.append('repeated_urls: repeated links are not independent evidence')
    if any(re.search(r'https?://(?:[^/]*\.)?(?:example\.(?:com|org|net|invalid)|[^/]*\.invalid)(?:/|$)', u) for u in unique_urls):
        warnings.append('example_source_url: example/reserved domains cannot substantiate a factual claim')
    for pattern in (r'全球第一|绝对领先|完全垄断', r'必然导致|直接决定|证明了.*因果', r'所有P[01].*已验证'):
        if re.search(pattern, text):
            warnings.append('assertion_review: inspect evidence and inference limits of strong claims')

    print(f'REPORT {args.report}')
    print(f'SCOPE mode={mode} required_modules={",".join(required)}')
    headings = len(re.findall(r'^#{1,4}\s+', text, re.M))
    tables = len(re.findall(r'^\|.*\|$', text, re.M))
    print(f'METRICS chars={len(text)} unique_urls={len(unique_urls)} table_rows={tables} headings={headings} (descriptive_only)')
    for item in failures: print('FAIL ' + item)
    for item in warnings: print('WARN ' + item)
    if not failures: print('PASS structural_checks_only')
    print('NOT_VERIFIED evidence_accuracy, source_availability, calculations, inference_quality, user_task_completion')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())

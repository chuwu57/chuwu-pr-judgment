#!/usr/bin/env python3
"""Run the five Follow Loop lane gates plus structure and trigger checks."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


STATE_REL = "Domains/PR/90-System/Follow-Loop/State.md"


def state_rows(path: Path) -> dict[str, list[str]]:
    rows: dict[str, list[str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) == 7 and cells[0] not in {"source_id", "---"}:
            if cells[0] in rows:
                raise ValueError(f"State来源ID重复：{cells[0]} ({path})")
            rows[cells[0]] = cells
    return rows


LANES = {'ai_follow', 'pr_follow', 'case_follow', 'embodied_follow', 'luxury_follow'}
MODES = {'deterministic': 2, 'best_effort': 3}


def source_registry(root: Path) -> dict:
    """Use the same YAML implementation already required by the KB's Ruby tools."""
    path = root / 'Domains/PR/90-System/Follow-Loop/Sources.yml'
    result = subprocess.run(['ruby', '-ryaml', '-rjson', '-rdate', '-e',
        'puts JSON.generate(YAML.safe_load(File.read(ARGV[0]), permitted_classes: [Date, Time], aliases: true))', str(path)],
        text=True, capture_output=True)
    if result.returncode:
        raise ValueError('无法读取Sources.yml：' + result.stderr.strip())
    document = json.loads(result.stdout)
    if not isinstance(document, dict):
        raise ValueError('Sources.yml必须是对象')
    rows = document.get('sources')
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError('Sources.yml.sources必须是对象数组')
    ids = [row.get('id') for row in rows]
    if any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('Sources.yml来源id缺失或重复')
    return dict(zip(ids, rows))


def resolved_source_lane(item: dict):
    """Match query_sources.rb: explicit lane, legacy routes, then the PR default."""
    if item.get('follow_lane') is not None:
        return item['follow_lane']
    legacy = item.get('lane', [])
    legacy = [legacy] if isinstance(legacy, str) else legacy
    if isinstance(legacy, list):
        if 'ai_person' in legacy:
            return 'ai_follow'
        if 'comms_case' in legacy:
            return 'case_follow'
    topics = item.get('topics', [])
    if isinstance(topics, list) and 'luxury-intelligence' in topics:
        return 'luxury_follow'
    return 'pr_follow'


def active_source_ids(root: Path) -> set[str]:
    return {key for key, value in source_registry(root).items() if value.get('active') is True}


def timestamp(value):
    """Accept an ISO date or an ISO timestamp with an explicit timezone."""
    from datetime import datetime, timezone
    if not isinstance(value, str):
        raise ValueError('日期必须是字符串')
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('时间戳必须带时区')
    return parsed.astimezone(timezone.utc)


def read_manifest(path: Path) -> dict:
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError('manifest必须是对象')
    sources = data.get('sources')
    if not isinstance(sources, list) or any(not isinstance(item, dict) for item in sources):
        raise ValueError('manifest.sources必须是对象数组')
    return data


def state_frontmatter(path: Path) -> dict[str, str]:
    match = re.match(r"\A---\n(.*?)\n---\n", path.read_text(encoding='utf-8'), re.S)
    if not match:
        return {}
    result = {}
    for line in match.group(1).splitlines():
        if ':' in line:
            key, value = line.split(':', 1)
            result[key.strip()] = value.strip().strip('"\'')
    return result


def validate_ai_audit_fields(baseline_path: Path, current_path: Path, by_id: dict) -> list[str]:
    """One AI audit contract for both the unified and standalone lane entrypoints."""
    old, new = state_frontmatter(baseline_path), state_frontmatter(current_path)
    errors = []
    for source_id, prefix in (('ai-builder-x-feed', 'x'), ('ai-builder-podcast-feed', 'podcast')):
        fields = {name: f'{prefix}_{name}' for name in
                  ('scanned_through', 'last_content_published_at', 'last_content_id', 'feed_commit')}
        item = by_id.get(source_id)
        if not item or item.get('status') != 'success':
            for state_field in fields.values():
                if old.get(state_field) != new.get(state_field):
                    errors.append(f'未成功AI来源推进了审计断点：{source_id}.{state_field}')
            continue
        try:
            if timestamp(new.get(fields['scanned_through'])) != timestamp(item.get('next_checkpoint')):
                errors.append(f'AI扫描审计水位与next_checkpoint不一致：{source_id}')
        except ValueError as exc:
            errors.append(f'AI扫描审计水位非法：{source_id} {exc}')
        for manifest_field, state_field in fields.items():
            if manifest_field in item and str(item[manifest_field]) != new.get(state_field):
                errors.append(f'AI manifest与State不一致：{source_id}.{manifest_field}')
    return errors


def validate_manifest(root: Path, baseline_path: Path, manifest_path: Path, *, data: dict | None = None) -> list[str]:
    errors = []
    try:
        baseline = state_rows(baseline_path)
        current = state_rows(root / STATE_REL)
        registry = source_registry(root)
        data = read_manifest(manifest_path) if data is None else data
    except (OSError, ValueError) as exc:
        return [f'manifest输入无法校验：{exc}']
    if not isinstance(data, dict):
        return ['manifest必须是对象']
    sources = data.get('sources')
    if not isinstance(sources, list) or any(not isinstance(item, dict) for item in sources):
        return ['manifest.sources必须是对象数组']
    active = {key for key, value in registry.items() if value.get('active') is True}
    ids = [item.get('source_id') for item in sources]
    if any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
        return ['manifest.source_id缺失或重复']
    selected = data.get('selected_source_ids', sorted(active))
    if (not isinstance(selected, list) or any(not isinstance(i, str) or not i for i in selected)
            or len(set(selected)) != len(selected) or not set(selected).issubset(active)):
        return ['selected_source_ids必须是活跃来源的无重复子集']
    if set(ids) != set(selected):
        errors.append('manifest未完整覆盖本轮selected_source_ids')
    if set(current) != set(baseline):
        errors.append('运行期间State来源集合必须保持不变；来源注册须先单独完成')
    if not set(current).issubset(registry) or not active.issubset(current):
        errors.append('State来源集合与Sources注册表不一致')
    by_id = dict(zip(ids, sources))
    for source_id, item in by_id.items():
        if not isinstance(item.get('lane'), str) or item['lane'] not in LANES:
            errors.append(f'manifest lane非法：{source_id}')
        registered = registry.get(source_id, {})
        registered_lane = resolved_source_lane(registered)
        if not isinstance(registered_lane, str) or registered_lane not in LANES:
            errors.append(f'Sources解析后的follow_lane非法：{source_id}')
        if item.get('lane') != registered_lane:
            errors.append(f'lane与Sources不一致：{source_id}')
        mode = item.get('coverage_mode')
        if not isinstance(mode, str) or mode not in MODES:
            errors.append(f'coverage_mode非法：{source_id}')
            continue
        if registered.get('coverage_mode') and registered['coverage_mode'] != mode:
            errors.append(f'coverage_mode与Sources不一致：{source_id}')
        status = item.get('status')
        if not isinstance(status, str):
            errors.append(f'manifest status必须是字符串：{source_id}')
            continue
        if status in {'failed', 'partial'}:
            if not isinstance(item.get('error'), str) or not item['error'].strip():
                errors.append(f'失败或部分覆盖来源缺少error：{source_id}')
            continue
        if status != 'success':
            errors.append(f'manifest status非法：{source_id}')
            continue
        for field in ('candidates_seen', 'valid_items'):
            value = item.get(field)
            if type(value) is not int or value < 0:
                errors.append(f'{field}必须是非负整数：{source_id}')
        if all(type(item.get(k)) is int for k in ('candidates_seen', 'valid_items')):
            if item['valid_items'] > item['candidates_seen']:
                errors.append(f'valid_items超过candidates_seen：{source_id}')
        try:
            start = timestamp(item.get('covered_from'))
            end = timestamp(item.get('covered_through'))
            next_at = timestamp(item.get('next_checkpoint'))
            requested_start = timestamp(item.get('requested_from', data.get('requested_from')))
            requested_end = timestamp(item.get('requested_through', data.get('requested_through')))
            if requested_start > requested_end or start > end:
                errors.append(f'覆盖窗口起止倒置：{source_id}')
            if start > requested_start or end < requested_end:
                errors.append(f'成功来源未覆盖请求窗口：{source_id}')
            if next_at != end:
                errors.append(f'next_checkpoint必须等于covered_through：{source_id}')
            old = baseline.get(source_id)
            if old and old[MODES[mode]] not in {'', '—', '-'} and next_at < timestamp(old[MODES[mode]]):
                errors.append(f'断点倒退：{source_id}')
            if old and old[1] != mode:
                errors.append(f'运行中不可切换覆盖模式：{source_id}')
        except ValueError as exc:
            errors.append(f'时间字段非法：{source_id} {exc}')
    for source_id, old_row in baseline.items():
        new_row = current.get(source_id)
        item = by_id.get(source_id)
        if not new_row:
            continue
        if not item or item.get('status') != 'success':
            if new_row != old_row:
                errors.append(f'未成功或范围外来源状态发生变化：{source_id}')
            continue
        mode = item.get('coverage_mode')
        if not isinstance(mode, str) or mode not in MODES:
            continue
        if new_row[1] != mode or new_row[MODES[mode]] != str(item.get('next_checkpoint')):
            errors.append(f'成功来源断点与manifest不一致：{source_id}')
        other_index = 3 if mode == 'deterministic' else 2
        if new_row[other_index] != old_row[other_index]:
            errors.append(f'成功来源改动了另一覆盖模式水位：{source_id}')
    writes = data.get('writes', [])
    if not isinstance(writes, list) or any(not isinstance(p, str) for p in writes):
        errors.append('manifest.writes必须是路径数组')
        writes = []
    if len(writes) != len(set(writes)):
        errors.append('manifest.writes不得重复')
    for path in writes:
        try:
            target = (root / path).resolve()
        except (OSError, ValueError) as exc:
            errors.append(f'写入路径非法：{path!r} {exc}')
            continue
        if Path(path).is_absolute() or '..' in Path(path).parts or not target.is_relative_to(root.resolve()):
            errors.append(f'写入路径必须在知识库内：{path}')
        elif not target.is_file():
            errors.append(f'已持久写入的文件不存在：{path}')
    if STATE_REL in writes and writes[-1] != STATE_REL:
        errors.append('State必须是最后一个持久写入项')
    if current != baseline and (not writes or writes[-1] != STATE_REL):
        errors.append('断点发生变化但manifest未把State列为最后写入')
    evidence_positions = [i for i, path in enumerate(writes) if '/Evidence/' in f'/{path}']
    prefixes = ('Domains/AI/Builders/', 'Domains/PR/10-Thinking/PR-Builders/',
                'Domains/AI/Embodied-Intelligence/', 'Domains/Business/Luxury/')
    assets = [i for i, path in enumerate(writes) if path.startswith(prefixes)]
    if evidence_positions and assets and max(evidence_positions) > min(assets):
        errors.append('manifest写入顺序必须先Evidence后人物／信号资产')
    errors.extend(validate_ai_audit_fields(baseline_path, root / STATE_REL, by_id))
    # This checks a declared write list and current files, not historical execution order or atomicity.
    return errors


def run_transaction_self_tests(root: Path) -> list[str]:
    result = subprocess.run([sys.executable, str(Path(__file__).with_name('test_follow_contract.py'))],
                            capture_output=True, text=True)
    print(result.stdout, end='')
    if result.returncode:
        return [result.stderr.strip() or 'Follow Loop contract tests failed']
    return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[4]))
    parser.add_argument("--baseline-state")
    parser.add_argument("--run-manifest")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--lanes", nargs="+", choices=sorted(LANES))
    args = parser.parse_args()
    if bool(args.baseline_state) != bool(args.run_manifest):
        parser.error("--baseline-state与--run-manifest必须成对提供")
    root = Path(args.root).resolve()
    scripts = root / "Skills/Knowledge-Intelligence/follow-loop/scripts"
    errors: list[str] = []

    expected_absent = [
        root / "Skills/Knowledge-Intelligence/ai-builders-follow",
        root / "Skills/Knowledge-Intelligence/pr-builders-follow",
        root / "Projects/Comms Sense v1.2",
        root / "Domains/AI/Builders/_System/AI-Builders-Follow-State.md",
    ]
    for path in expected_absent:
        if path.exists():
            errors.append(f"旧运行入口仍存在：{path.relative_to(root)}")

    manifest_data = None
    if args.baseline_state and args.run_manifest:
        try:
            manifest_data = read_manifest(Path(args.run_manifest))
            errors.extend(validate_manifest(root, Path(args.baseline_state), Path(args.run_manifest), data=manifest_data))
        except (OSError, ValueError, KeyError) as exc:
            errors.append(f"manifest门禁无法执行：{exc}")
    if args.self_test:
        transaction_errors = run_transaction_self_tests(root)
        errors.extend(transaction_errors)
        if not transaction_errors:
            print("PASS: Follow Loop contract regression suite")

    triggers = ("启动Follow Loop，更新一下", "FL一下")
    entry_files = (
        "AGENTS.md",
        "README.md",
        "Skills/README.md",
        "Domains/PR/45-Workflows/Workflow_Follow-Loop.md",
        "Skills/Knowledge-Intelligence/follow-loop/SKILL.md",
    )
    for relative in entry_files:
        path = root / relative
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        for trigger in triggers:
            if trigger not in text:
                errors.append(f"缺少精确触发词：{relative} {trigger}")
    config_text = (root / "Domains/PR/90-System/Follow-Loop/Config.yml").read_text(encoding="utf-8")
    if 'aliases: ["FL一下"]' not in config_text:
        errors.append("Config.yml未登记FL一下别名")
    obsolete_triggers = ("Sense一下", "雷达启动", "$ai-builders-follow", "$pr-builders-follow", "AI Builders Follow", "PR Builders Follow", "Comms Sense")
    for relative in entry_files:
        text = (root / relative).read_text(encoding="utf-8")
        for obsolete in obsolete_triggers:
            if obsolete in text:
                errors.append(f"入口文档仍含旧触发或旧Skill名：{relative} {obsolete}")

    open_query = subprocess.run(
        ["ruby", str(scripts / "query_state.rb"), "open"],
        cwd=root,
        text=True,
        capture_output=True,
    )
    if open_query.returncode:
        errors.append(open_query.stderr.strip() or "query_state.rb open执行失败")

    commands = [
        [sys.executable, str(scripts / "validate_ai_lane.py"), "--root", str(root)],
        [sys.executable, str(scripts / "validate_pr_lane.py"), "--root", str(root)],
        ["ruby", str(scripts / "validate_case_follow.rb")],
        [sys.executable, str(scripts / "validate_embodied_lane.py"), "--root", str(root)],
        [sys.executable, str(scripts / "validate_luxury_lane.py"), "--root", str(root)],
    ]
    lane_order = ["ai_follow", "pr_follow", "case_follow", "embodied_follow", "luxury_follow"]
    selected_lanes = set(args.lanes or lane_order)
    if manifest_data is not None:
        selected_lanes = {item["lane"] for item in manifest_data["sources"]
                          if isinstance(item.get("lane"), str) and item["lane"] in LANES}
    commands = [command for lane, command in zip(lane_order, commands) if lane in selected_lanes]

    for command in commands:
        result = subprocess.run(command, cwd=root, text=True, capture_output=True)
        print(result.stdout, end="")
        if result.returncode:
            errors.append(result.stderr.strip() or f"lane验证失败：{' '.join(command)}")

    if errors:
        print("FAIL: Follow Loop harness")
        for error in errors:
            print(f"- {error}")
        return 1
    print("PASS: Follow Loop harness")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

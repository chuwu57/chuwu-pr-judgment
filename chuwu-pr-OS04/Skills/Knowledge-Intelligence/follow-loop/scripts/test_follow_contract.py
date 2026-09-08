#!/usr/bin/env python3
"""Behavioral tests with isolated source/state files; never mutate the real KB."""
import json
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
from validate_follow_loop import validate_manifest, STATE_REL
from validate_pr_lane import validate_signal_stages
from validate_ai_lane import validate as validate_ai_lane


class ManifestContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='follow-contract-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = self.root / STATE_REL
        self.state.parent.mkdir(parents=True)
        (self.state.parent/'Sources.yml').write_text('sources:\n  - id: a\n    active: true\n    follow_lane: ai_follow\n    coverage_mode: deterministic\n  - id: b\n    active: true\n    follow_lane: luxury_follow\n    coverage_mode: best_effort\n')
        self.before = '| source_id | coverage_mode | scanned_through | searched_through | last_content_published_at | last_content_id | last_status |\n| --- | --- | --- | --- | --- | --- | --- |\n| a | deterministic | 2026-08-01T00:00:00Z | — | — | — | success |\n| b | best_effort | — | 2026-08-01T00:00:00Z | — | — | success |\n'
        self.after = self.before.replace('| a | deterministic | 2026-08-01T00:00:00Z', '| a | deterministic | 2026-08-02T00:00:00Z')
        self.baseline = self.root/'baseline.md'
        self.baseline.write_text(self.before)
        self.manifest = self.root/'manifest.json'
        self.data = {'requested_from':'2026-08-01T00:00:00Z','requested_through':'2026-08-02T00:00:00Z',
            'sources':[{'source_id':'a','lane':'ai_follow','coverage_mode':'deterministic','status':'success',
                'covered_from':'2026-08-01T00:00:00Z','covered_through':'2026-08-02T00:00:00Z',
                'next_checkpoint':'2026-08-02T00:00:00Z','candidates_seen':2,'valid_items':1},
                {'source_id':'b','lane':'luxury_follow','coverage_mode':'best_effort','status':'failed','error':'unavailable'}],
            'writes':[STATE_REL]}

    def check(self, valid, data=None, state=None):
        self.manifest.write_text(json.dumps(self.data if data is None else data))
        self.state.write_text(self.after if state is None else state)
        errors = validate_manifest(self.root,self.baseline,self.manifest)
        self.assertEqual(not errors,valid,errors)

    def test_success_and_failed_frozen(self): self.check(True)
    def test_explicit_subset(self):
        self.data['selected_source_ids']=['a'];self.data['sources']=self.data['sources'][:1];self.check(True)
    def test_unannounced_subset(self):
        self.data['sources']=self.data['sources'][:1];self.check(False)
    def test_outside_scope_mutation(self):
        self.data['selected_source_ids']=['a'];self.data['sources']=self.data['sources'][:1]
        self.check(False,state=self.after.replace('| b | best_effort | — | 2026-08-01','| b | best_effort | — | 2026-08-02'))
    def test_future_checkpoint(self):
        self.data['sources'][0]['next_checkpoint']='2099-01-01T00:00:00Z'
        self.check(False,state=self.after.replace('2026-08-02','2099-01-01'))
    def test_backwards_even_when_window_matches(self):
        self.data['requested_from']='2020-01-01T00:00:00Z';self.data['requested_through']='2020-01-02T00:00:00Z'
        self.data['sources'][0].update(covered_from=self.data['requested_from'],covered_through=self.data['requested_through'],next_checkpoint=self.data['requested_through'])
        self.check(False,state=self.after.replace('2026-08-02','2020-01-02'))
    def test_negative_count(self): self.data['sources'][0]['candidates_seen']=-2;self.check(False)
    def test_boolean_count(self): self.data['sources'][0]['candidates_seen']=True;self.check(False)
    def test_valid_exceeds_candidates(self): self.data['sources'][0]['valid_items']=3;self.check(False)
    def test_missing_persisted_file(self): self.data['writes'].insert(0,'Domains/AI/Builders/absent.md');self.check(False)
    def test_unknown_state_source(self): self.check(False,state=self.after+'| x | deterministic | 2026-08-02 | — | — | — | success |\n')
    def test_bad_source_type(self): self.data['sources']=[None];self.check(False)
    def test_bad_mode(self): self.data['sources'][0]['coverage_mode']='magic';self.check(False)
    def test_wrong_lane(self): self.data['sources'][0]['lane']='pr_follow';self.check(False)
    def test_invalid_date(self): self.data['sources'][0]['covered_from']='not-a-date';self.check(False)
    def test_timezone_comparison(self):
        self.data['sources'][0]['covered_through']='2026-08-02T08:00:00+08:00';self.check(True)
    def test_state_not_last(self):
        path=self.root/'Domains/AI/Builders/a.md';path.parent.mkdir(parents=True);path.write_text('asset')
        self.data['writes'].append('Domains/AI/Builders/a.md');self.check(False)
    def test_actual_evidence_before_asset(self):
        paths=['Domains/PR/60-References/Evidence/a.md','Domains/AI/Builders/a.md']
        for name in paths:
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('fixture')
        self.data['writes']=paths+[STATE_REL];self.check(True)
        self.data['writes']=list(reversed(paths))+[STATE_REL];self.check(False)
    def test_partial_frozen(self):
        self.data['sources'][0].update(status='partial',error='history missing');self.data['writes']=[];self.check(True,state=self.before)
        self.check(False)
    def test_unknown_selection(self): self.data['selected_source_ids']=['x'];self.check(False)
    def test_escape_path(self): self.data['writes'].insert(0,'../outside.md');self.check(False)


    def test_duplicate_current_source_is_not_overwritten(self):
        self.check(False, state=self.after + self.after.splitlines()[2] + '\n')

    def test_duplicate_baseline_source_is_not_overwritten(self):
        self.baseline.write_text(self.before + self.before.splitlines()[2] + '\n')
        self.check(False)

    def test_registry_root_must_be_mapping(self):
        (self.state.parent/'Sources.yml').write_text('- invalid-root\n')
        self.check(False)

    def test_registry_implicit_pr_lane(self):
        path = self.state.parent/'Sources.yml'
        path.write_text(path.read_text().replace('    follow_lane: ai_follow\n', ''))
        self.data['sources'][0]['lane'] = 'pr_follow'
        self.check(True)
        self.data['sources'][0]['lane'] = 'ai_follow'
        self.check(False)

    def test_registry_legacy_route_resolves_ai_lane(self):
        path = self.state.parent/'Sources.yml'
        path.write_text(path.read_text().replace('    follow_lane: ai_follow\n', '    lane: [ai_person]\n'))
        self.check(True)
        self.data['sources'][0]['lane'] = 'pr_follow'
        self.check(False)

    def test_missing_lane_rejected(self):
        self.data['sources'][0].pop('lane')
        self.check(False)

    def test_missing_coverage_mode_rejected(self):
        self.data['sources'][0].pop('coverage_mode')
        self.check(False)

    def test_lane_container_returns_error(self):
        self.data['sources'][0]['lane'] = ['ai_follow']
        self.check(False)

    def test_mode_container_returns_error(self):
        self.data['sources'][0]['coverage_mode'] = {'mode': 'deterministic'}
        self.check(False)

    def test_status_container_returns_error(self):
        self.data['sources'][0]['status'] = ['success']
        self.check(False)

    def test_manifest_invalid_json_returns_error(self):
        self.state.write_text(self.after)
        self.manifest.write_text('{invalid')
        self.assertTrue(validate_manifest(self.root, self.baseline, self.manifest))

    def test_manifest_source_shapes_return_error(self):
        for sources in (None, 'text', {}, [None], [42]):
            with self.subTest(sources=sources):
                self.check(False, data={**self.data, 'sources': sources})

    def ai_fixture(self):
        source_id = 'ai-builder-x-feed'
        source_file = self.state.parent/'Sources.yml'
        source_file.write_text(source_file.read_text().replace('id: a\n', f'id: {source_id}\n'))
        prefix = ('---\nskill: follow-loop\nx_scanned_through: "{watermark}"\n'
                  'x_last_content_published_at: "2026-07-30T00:00:00Z"\n'
                  'x_last_content_id: original\nx_feed_commit: old-commit\n---\n')
        self.before = prefix.format(watermark='2026-08-01T00:00:00Z') + self.before.replace('| a |', f'| {source_id} |')
        self.after = prefix.format(watermark='2026-08-02T00:00:00Z') + self.after.replace('| a |', f'| {source_id} |')
        self.baseline.write_text(self.before)
        self.data['sources'][0]['source_id'] = source_id
        return source_id

    def test_ai_audit_mirrors_success_checkpoint(self):
        self.ai_fixture()
        self.check(True)
        self.check(False, state=self.after.replace('x_scanned_through: "2026-08-02', 'x_scanned_through: "2099-01-01'))

    def test_ai_failed_source_freezes_frontmatter(self):
        self.ai_fixture()
        self.data['sources'][0].update(status='failed', error='unavailable')
        self.data['writes'] = []
        self.check(True, state=self.before)
        self.check(False, state=self.before.replace('old-commit', 'unapproved-commit'))

    def test_ai_standalone_uses_shared_manifest_contract(self):
        self.ai_fixture()
        self.check(True)
        # The legacy standalone code only compared optional audit fields and missed this.
        self.data['sources'][0]['next_checkpoint'] = '2099-01-01T00:00:00Z'
        self.manifest.write_text(json.dumps(self.data))
        errors = validate_ai_lane(self.root, self.baseline, self.manifest)
        self.assertTrue(any('next_checkpoint必须等于covered_through' in error for error in errors), errors)

    def test_ai_standalone_requires_paired_inputs(self):
        self.state.write_text(self.before)
        errors = validate_ai_lane(self.root, self.baseline, None)
        self.assertTrue(any('必须成对提供' in error for error in errors), errors)

    def test_harness_malformed_manifest_does_not_reparse_or_traceback(self):
        self.state.write_text(self.after)
        entries = ('AGENTS.md', 'README.md', 'Skills/README.md',
                   'Domains/PR/45-Workflows/Workflow_Follow-Loop.md',
                   'Skills/Knowledge-Intelligence/follow-loop/SKILL.md')
        for relative in entries:
            path = self.root/relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('启动Follow Loop，更新一下\nFL一下\n')
        (self.state.parent/'Config.yml').write_text('aliases: ["FL一下"]\n')
        for value in ('{invalid', json.dumps({'sources': None}), json.dumps({'sources': ['text']})):
            with self.subTest(manifest=value):
                self.manifest.write_text(value)
                result = subprocess.run([sys.executable, str(Path(__file__).with_name('validate_follow_loop.py')),
                    '--root', str(self.root), '--baseline-state', str(self.baseline), '--run-manifest', str(self.manifest)],
                    capture_output=True, text=True)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn('manifest门禁无法执行', result.stdout)
                self.assertNotIn('Traceback', result.stdout + result.stderr)

    def test_signal_upgrade_evidence(self):
        body='### Example\n- 信号阶段：形成中趋势\n- 独立主体：A；B；C\n- 来源类型：研究；行动\n- 行动／案例／研究证据：[source](https://example.org/study)\n'
        self.assertEqual(validate_signal_stages(body), [])
        self.assertTrue(validate_signal_stages(body.replace('A；B；C', 'A；A；B')))
        self.assertTrue(validate_signal_stages(body.replace('研究；行动', '研究')))
        self.assertTrue(validate_signal_stages(body.replace('https://example.org/study', '未核验')))

    def test_stable_signal_requires_cycles(self):
        body='### Example\n- 信号阶段：稳定趋势\n- 独立主体：A；B；C\n- 来源类型：研究；行动\n- 行动／案例／研究证据：https://example.org/study\n'
        self.assertTrue(validate_signal_stages(body))
        self.assertTrue(validate_signal_stages(body+'- 成功扫描周期：1\n'))
        self.assertEqual(validate_signal_stages(body+'- 成功扫描周期：2\n'), [])


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(ManifestContract))
    print(f'Follow manifest: {result.testsRun} behavioral tests; success={result.wasSuccessful()}')
    raise SystemExit(0 if result.wasSuccessful() else 1)

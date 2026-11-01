"""Synthetic behavior tests; never invoke Android or change real packages."""
import argparse
import contextlib
import copy
import io
import json
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import phone
import ui_controls as ui

IDENTITY = {'key': 'synthetic-device', 'build': 'test-build', 'model': 'test'}


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'record.json'
        self.state = {'test.default': 0, 'test.enabled': 1, 'test.disabled': 3}
        self.calls = []
        self.failure = None
        self.addCleanup(patch.stopall)
        patch.object(phone, 'device', return_value=IDENTITY).start()
        patch.object(phone, 'package_state', side_effect=lambda p, u: self.state[p]).start()
        patch.object(phone, 'android', side_effect=self.command).start()

    def command(self, *args, **kwargs):
        self.calls.append(args)
        name = args[-1]
        if name == self.failure:
            raise RuntimeError('synthetic failure')
        self.state[name] = {v: k for k, v in phone.STATES.items()}[args[1]]
        return ''

    def disable(self, *names):
        with contextlib.redirect_stdout(io.StringIO()):
            phone.disable(names, 0, self.path)

    def test_restore_preserves_default_explicit_and_preexisting_disabled(self):
        original = self.state.copy()
        self.disable(*self.state)
        self.assertEqual(set(self.state.values()), {3})
        phone.restore(self.path, 0)
        self.assertEqual(self.state, original)
        self.assertFalse(any(c[-1] == 'test.disabled' for c in self.calls))
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        previous = len(self.calls)
        phone.restore(self.path, 0)
        self.assertEqual(len(self.calls), previous)

    def test_restore_all_enabled_modes(self):
        self.state = {f'test.state{i}': i for i in range(5)}
        original = self.state.copy()
        self.disable(*self.state)
        phone.restore(self.path, 0)
        self.assertEqual(self.state, original)

    def test_partial_failure_keeps_recoverable_journal(self):
        self.failure = 'test.enabled'
        with self.assertRaises(RuntimeError):
            self.disable('test.default', 'test.enabled', 'test.disabled')
        record = json.loads(self.path.read_text())
        self.assertTrue(record['entries']['test.enabled']['attempted'])
        self.assertFalse(record['entries']['test.disabled']['attempted'])
        self.failure = None
        phone.restore(self.path, 0)
        self.assertEqual(self.state['test.default'], 0)
        self.assertEqual(self.state['test.enabled'], 1)

    def test_completed_restore_does_not_undo_later_disable(self):
        self.disable('test.default')
        phone.restore(self.path, 0)
        for later in (3, 2):
            with self.subTest(later=later):
                self.state['test.default'] = later
                previous = len(self.calls)
                result = phone.restore(self.path, 0)
                self.assertEqual(self.state['test.default'], later)
                self.assertEqual(len(self.calls), previous)
                self.assertEqual(result['restored'], [])

    def test_partial_restore_retry_skips_completed_items(self):
        self.disable('test.default', 'test.enabled')
        self.failure = 'test.enabled'
        with self.assertRaises(RuntimeError):
            phone.restore(self.path, 0)
        record = json.loads(self.path.read_text())
        self.assertTrue(record['entries']['test.default']['restored'])
        self.assertNotIn('restored', record['entries']['test.enabled'])
        self.state['test.default'] = 3
        self.failure = None
        previous = len(self.calls)
        result = phone.restore(self.path, 0)
        self.assertEqual(self.state['test.default'], 3)
        self.assertEqual(self.state['test.enabled'], 1)
        self.assertEqual(result['restored'], ['test.enabled'])
        self.assertEqual([c[-1] for c in self.calls[previous:]], ['test.enabled'])

    def test_restore_via_symlink_updates_original_and_preserves_link(self):
        self.disable('test.default')
        link = self.path.with_name('link.json')
        link.symlink_to(self.path.name)
        result = phone.restore(link, 0)
        self.assertTrue(link.is_symlink())
        self.assertEqual(result['record'], str(self.path.resolve()))
        self.assertTrue(json.loads(self.path.read_text())['entries']['test.default']['restored'])
        self.state['test.default'] = 3
        previous = len(self.calls)
        phone.restore(self.path, 0)
        phone.restore(link, 0)
        self.assertEqual(self.state['test.default'], 3)
        self.assertEqual(len(self.calls), previous)

    def test_partial_restore_through_link_chain_can_resume_original(self):
        self.disable('test.default', 'test.enabled')
        link = self.path.with_name('link.json')
        link.symlink_to(self.path.name)
        chain = self.path.with_name('chain.json')
        chain.symlink_to(link.name)
        self.failure = 'test.enabled'
        with self.assertRaises(RuntimeError):
            phone.restore(chain, 0)
        self.assertTrue(link.is_symlink())
        self.assertTrue(chain.is_symlink())
        self.assertTrue(json.loads(self.path.read_text())['entries']['test.default']['restored'])
        self.state['test.default'] = 3
        self.failure = None
        phone.restore(self.path, 0)
        self.assertEqual(self.state['test.default'], 3)
        self.assertEqual(self.state['test.enabled'], 1)

    def test_broken_record_link_does_not_change_packages(self):
        link = self.path.with_name('broken.json')
        link.symlink_to('missing.json')
        with self.assertRaises(FileNotFoundError):
            phone.restore(link, 0)
        self.assertTrue(link.is_symlink())
        self.assertEqual(self.calls, [])

    def test_other_device_cannot_restore(self):
        self.disable('test.default')
        with patch.object(phone, 'device', return_value={'key': 'other'}):
            with self.assertRaises(RuntimeError):
                phone.restore(self.path, 0)
        self.assertEqual(self.state['test.default'], 3)

    def test_other_user_cannot_restore(self):
        self.disable('test.default')
        with self.assertRaises(RuntimeError):
            phone.restore(self.path, 10)
        self.assertEqual(len(self.calls), 1)

    def test_later_state_change_is_not_overwritten(self):
        self.disable('test.default')
        self.state['test.default'] = 1
        with self.assertRaises(RuntimeError):
            phone.restore(self.path, 0)
        self.assertEqual(self.state['test.default'], 1)

    def test_existing_record_not_overwritten(self):
        self.path.write_text('keep')
        with self.assertRaises(FileExistsError):
            self.disable('test.default')
        self.assertEqual(self.path.read_text(), 'keep')
        self.assertEqual(self.calls, [])

    def test_component_and_shell_input_rejected(self):
        for value in ['test.app/Activity', 'test.app;id', '--user', '$(id)']:
            with self.assertRaises(RuntimeError):
                self.disable(value)
        self.assertEqual(self.calls, [])


class SnapshotTests(unittest.TestCase):
    def test_parse_per_user_states(self):
        raw = '''Packages:
  Package [test.app] (123):
    User 0: installed=true stopped=false hidden=false suspended=false enabled=0
    User 10: installed=true stopped=true hidden=false suspended=false enabled=3
  Package [test.other] (124):
    User 0: installed=false enabled=0
'''
        self.assertEqual(phone.parse_packages(raw, 0)['test.app']['enabled'], 0)
        self.assertEqual(phone.parse_packages(raw, 10)['test.app']['enabled'], 3)
        self.assertNotIn('test.other', phone.parse_packages(raw, 0))

    def test_hidden_system_package_never_overrides_current_state(self):
        raw = """Packages:
  Package [test.updated] (1):
    User 0: installed=true enabled=3 stopped=true hidden=false suspended=false
    User 10: installed=true enabled=1 stopped=false hidden=false suspended=false
Hidden system packages:
  Package [test.updated] (2):
    User 0: installed=true enabled=0 stopped=false hidden=false suspended=false
    User 10: installed=true enabled=0 stopped=false hidden=false suspended=false
  Package [test.hidden_only] (3):
    User 0: installed=true enabled=0
"""
        self.assertEqual(phone.parse_packages(raw, 0)['test.updated']['enabled'], 3)
        self.assertEqual(phone.parse_packages(raw, 10)['test.updated']['enabled'], 1)
        self.assertNotIn('test.hidden_only', phone.parse_packages(raw, 0))
        with patch.object(phone, 'android', return_value=raw):
            self.assertEqual(phone.package_state('test.updated', 0), 3)
        with patch.object(phone, 'android', return_value=raw), patch.object(phone, 'package_names', return_value={'test.updated'}):
            self.assertEqual(phone.packages(0)['test.updated']['enabled'], 3)

    def test_other_sections_and_missing_header_are_not_current_packages(self):
        raw = """Hidden system packages:
  Package [test.hidden] (1):
    User 0: installed=true enabled=0
Packages:
  Package [test.active] (2):
    User 0: installed=true enabled=3
Other section:
    User 0: installed=true enabled=0
  Package [test.other] (3):
    User 0: installed=true enabled=0
"""
        self.assertEqual(set(phone.parse_packages(raw, 0)), {'test.active'})
        self.assertEqual(phone.parse_packages(raw, 0)['test.active']['enabled'], 3)
        self.assertEqual(phone.parse_packages('  Package [test.unknown] (1):\n    User 0: installed=true enabled=0', 0), {})

    def test_reboot_and_stopped_do_not_imply_reenabled(self):
        before = {'kind': 'snapshot', 'device': IDENTITY, 'user': 0, 'boot_id': 'a',
                  'packages': {'test.app': {'enabled': 3, 'disabled': True, 'stopped': True}}}
        after = copy.deepcopy(before)
        after['boot_id'] = 'b'
        after['packages']['test.app']['stopped'] = False
        result = phone.compare(before, after)
        self.assertTrue(result['rebooted'])
        self.assertEqual(result['changed']['test.app']['after']['enabled'], 3)
        after['device'] = {'key': 'other', 'build': 'test'}
        with self.assertRaises(RuntimeError):
            phone.compare(before, after)

    def test_private_outputs_outside_repository(self):
        with self.assertRaises(RuntimeError):
            phone.private_path(Path(__file__).parent / 'private.json')


XML = '''<hierarchy><node package="test.app" text="" enabled="true" clickable="true" bounds="[0,0][100,100]">
<node package="test.app" text="Settings" resource-id="test.app:id/settings" enabled="true" clickable="false" bounds="[10,10][60,40]"/>
<node password="true" text="secret" bounds="[0,0][30,20]"><node text="nested secret" bounds="[0,0][20,10]"/></node>
</node></hierarchy>'''


class UITests(unittest.TestCase):
    def setUp(self):
        self.rows = ui.controls(XML)
        self.args = argparse.Namespace(text='Settings', id='', exact=True,
                                       expect_text='Details', expect_id='', wait=0)

    def test_parent_click_target_and_password_exclusion(self):
        self.assertEqual(len(self.rows), 1)
        self.assertFalse(self.rows[0]['clickable'])
        self.assertEqual(self.rows[0]['tap_center'], [50, 50])

    def test_disabled_clickable_parent_is_not_a_valid_fallback(self):
        rows = ui.controls(XML.replace('enabled="true" clickable="true"', 'enabled="false" clickable="true"'))
        self.assertTrue(rows[0]['enabled'])
        with self.assertRaises(RuntimeError):
            ui.unique_target(rows)

    def test_enabled_button_inside_disabled_container_can_be_clicked(self):
        xml = """<hierarchy><node enabled="false" clickable="false" bounds="[0,0][300,100]">
<node text="Settings" enabled="true" clickable="true" bounds="[0,0][100,100]"/>
</node></hierarchy>"""
        rows = ui.controls(xml)
        self.assertTrue(rows[0]['enabled'])
        self.assertTrue(rows[0]['clickable'])
        self.args.expect_text = ''
        with patch.object(ui, 'dump_controls', return_value=rows), patch.object(ui, 'android') as command:
            ui.tap(self.args, rows)
            command.assert_called_once_with('input', 'tap', 50, 50)

    def test_parent_center_over_other_button_never_sends_tap(self):
        for attrs in ('text="Delete"', '', 'password="true" text="private"', 'enabled="false" text="Delete"'):
            with self.subTest(blocker=attrs):
                xml = f"""<hierarchy><node enabled="true" clickable="true" bounds="[0,0][300,100]">
<node text="Open" enabled="true" clickable="false" bounds="[0,0][100,100]"/>
<node {attrs} clickable="true" bounds="[100,0][200,100]"/>
</node></hierarchy>"""
                rows = ui.controls(xml)
                selected = ui.matching(rows, 'Open', exact=True)
                self.args.text = 'Open'
                with patch.object(ui, 'dump_controls', return_value=rows), patch.object(ui, 'android') as command:
                    with self.assertRaises(RuntimeError):
                        ui.tap(self.args, selected)
                    command.assert_not_called()
                self.assertNotIn('private', str(rows))

    def test_nonoverlapping_sibling_does_not_block_parent_target(self):
        xml = """<hierarchy><node enabled="true" clickable="true" bounds="[0,0][300,100]">
<node text="Open" enabled="true" clickable="false" bounds="[0,0][100,100]"/>
<node text="Delete" enabled="true" clickable="true" bounds="[200,0][300,100]"/>
</node></hierarchy>"""
        target = ui.unique_target(ui.matching(ui.controls(xml), 'Open', exact=True))
        self.assertEqual(target['tap_center'], [150, 50])

    def test_disabled_clickable_ancestor_does_not_block_enabled_child_button(self):
        xml = """<hierarchy><node enabled="false" clickable="true" bounds="[0,0][300,100]">
<node text="Open" enabled="true" clickable="true" bounds="[0,0][100,100]"/>
</node></hierarchy>"""
        self.assertEqual(ui.unique_target(ui.controls(xml))['tap_center'], [50, 50])

    def test_long_clickable_sibling_blocks_parent_center(self):
        for attrs in ('enabled="true"', 'enabled="false"', 'enabled="true" password="true"'):
            with self.subTest(attrs=attrs):
                xml = f"""<hierarchy><node enabled="true" clickable="true" bounds="[0,0][300,100]">
<node text="Open" enabled="true" clickable="false" bounds="[0,0][100,100]"/>
<node {attrs} clickable="false" long-clickable="true" bounds="[100,0][200,100]"/>
</node></hierarchy>"""
                rows = ui.controls(xml)
                self.args.text = 'Open'
                with patch.object(ui, 'dump_controls', return_value=rows), patch.object(ui, 'android') as command:
                    with self.assertRaises(RuntimeError):
                        ui.tap(self.args, ui.matching(rows, 'Open', exact=True))
                    command.assert_not_called()

    def test_long_clickable_ancestor_is_not_skipped_for_outer_button(self):
        xml = """<hierarchy><node enabled="true" clickable="true" bounds="[0,0][300,100]">
<node enabled="true" clickable="false" long-clickable="true" bounds="[0,0][100,100]">
<node text="Open" enabled="true" clickable="false" bounds="[0,0][40,40]"/>
</node></node></hierarchy>"""
        with self.assertRaises(RuntimeError):
            ui.unique_target(ui.controls(xml))

    def test_long_clickable_label_does_not_fall_back_to_parent(self):
        xml = """<hierarchy><node enabled="true" clickable="true" bounds="[0,0][300,100]">
<node text="Open" enabled="true" clickable="false" long-clickable="true" bounds="[0,0][100,100]"/>
</node></hierarchy>"""
        rows = ui.controls(xml)
        with self.assertRaises(RuntimeError):
            ui.unique_target(rows)
        self.assertTrue(rows[0]['long_clickable'])

    def test_unknown_long_clickable_bounds_reject_tap(self):
        rows = ui.controls(XML.replace('</hierarchy>', '<node long-clickable="true"/></hierarchy>'))
        with self.assertRaises(RuntimeError):
            ui.unique_target(rows)

    def test_clickable_button_inside_long_clickable_container_is_valid(self):
        xml = """<hierarchy><node enabled="true" clickable="false" long-clickable="true" bounds="[0,0][300,100]">
<node text="Open" enabled="true" clickable="true" bounds="[0,0][100,100]"/>
</node></hierarchy>"""
        self.assertEqual(ui.unique_target(ui.controls(xml))['tap_center'], [50, 50])

    def test_own_center_over_overlapping_sibling_is_rejected(self):
        xml = """<hierarchy>
<node text="Open" enabled="true" clickable="true" bounds="[0,0][100,100]"/>
<node enabled="true" clickable="true" bounds="[20,20][80,80]"/>
</hierarchy>"""
        with self.assertRaises(RuntimeError):
            ui.unique_target(ui.matching(ui.controls(xml), 'Open', exact=True))

    def test_new_blocker_before_tap_is_rejected(self):
        fresh = ui.controls(XML.replace('</hierarchy>', '<node clickable="true" bounds="[40,40][60,60]"/></hierarchy>'))
        with patch.object(ui, 'dump_controls', return_value=fresh), patch.object(ui, 'android') as command:
            with self.assertRaises(RuntimeError):
                ui.tap(self.args, self.rows)
            command.assert_not_called()

    def test_disabled_button_keeps_own_clickable_flag_but_cannot_be_target(self):
        rows = ui.controls('<hierarchy><node text="Open" enabled="false" clickable="true" bounds="[0,0][100,100]"/></hierarchy>')
        self.assertFalse(rows[0]['enabled'])
        self.assertTrue(rows[0]['clickable'])
        with self.assertRaises(RuntimeError):
            ui.unique_target(rows)

    def test_clickable_with_unknown_bounds_prevents_guessing(self):
        rows = ui.controls(XML.replace('</hierarchy>', '<node clickable="true"/></hierarchy>'))
        with self.assertRaises(RuntimeError):
            ui.unique_target(rows)

    def test_ambiguous_match_sends_no_tap(self):
        with patch.object(ui, 'android') as command:
            with self.assertRaises(RuntimeError):
                ui.tap(self.args, self.rows * 2)
            command.assert_not_called()

    def test_moved_target_sends_no_tap(self):
        moved = copy.deepcopy(self.rows)
        moved[0]['tap_center'] = [100, 100]
        with patch.object(ui, 'dump_controls', return_value=moved), patch.object(ui, 'android') as command:
            with self.assertRaises(RuntimeError):
                ui.tap(self.args, self.rows)
            command.assert_not_called()

    def test_expected_existing_before_click_is_rejected(self):
        self.args.expect_text = 'Settings'
        with patch.object(ui, 'dump_controls', return_value=self.rows), patch.object(ui, 'android') as command:
            with self.assertRaises(RuntimeError):
                ui.tap(self.args, self.rows)
            command.assert_not_called()

    def test_click_once_and_verify_new_result(self):
        after = copy.deepcopy(self.rows)
        after[0]['text'] = 'Details'
        with patch.object(ui, 'dump_controls', side_effect=[self.rows, after]), patch.object(ui, 'android') as command:
            result = ui.tap(self.args, self.rows)
            self.assertTrue(result['verified'])
            command.assert_called_once_with('input', 'tap', 50, 50)

    def test_failed_verification_never_retries_tap(self):
        with patch.object(ui, 'dump_controls', return_value=self.rows), patch.object(ui, 'android') as command:
            result = ui.tap(self.args, self.rows)
            self.assertFalse(result['verified'])
            command.assert_called_once()

    def test_no_expectation_does_not_claim_success(self):
        self.args.expect_text = ''
        with patch.object(ui, 'dump_controls', return_value=self.rows), patch.object(ui, 'android'):
            self.assertFalse(ui.tap(self.args, self.rows)['verified'])

    def test_dump_failure_after_tap_reports_sent_without_retry(self):
        with patch.object(ui, 'dump_controls', side_effect=[self.rows, RuntimeError('offline')]), patch.object(ui, 'android') as command:
            result = ui.tap(self.args, self.rows)
            self.assertTrue(result['tap_sent'])
            self.assertFalse(result['verified'])
            command.assert_called_once()


class VibrationTests(unittest.TestCase):
    def test_android_command_environment_isolated_and_errors_propagate(self):
        script = Path(__file__).resolve().parents[3] / 'scripts/vibrate.sh'
        # Source in a shell with stubbed cmd/exec; never reach Android's vibrator.
        harness = """
cmd() {
    printf '%s|%s|%s|%s\\n' "${LD_LIBRARY_PATH-unset}" "${LD_PRELOAD-unset}" "${LD_AUDIT-unset}" "$*" >&3
    return 7
}
exec() { "$@"; }
export LD_LIBRARY_PATH=synthetic LD_PRELOAD=synthetic LD_AUDIT=synthetic
vibration_script="$1"\nset -- 125\n. "$vibration_script"
"""
        # Redirect FD 3 before the script can suppress stdout/stderr.
        result = subprocess.run(['bash', '-c', 'exec 3>&1\n' + harness, 'test', str(script)],
                                capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), 'unset|unset|unset|vibrator_manager synced -f oneshot 125')
        self.assertEqual(result.returncode, 7)


if __name__ == '__main__':
    unittest.main()

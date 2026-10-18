import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bootstrap_model import evaluate, Gate, outcome


class BootstrapModelTest(unittest.TestCase):
    def test_unknown_runtime_flags_are_not_a_success(self):
        routes = evaluate()
        self.assertEqual(routes[-1]['outcome'], 'unverified')
        self.assertEqual(routes[0]['outcome'], 'unverified')
        self.assertTrue(all(row['outcome'] == 'blocked' for row in routes[1:-1]))

    def test_disabled_qr_and_legacy_receiver_leave_no_candidate_in_this_model(self):
        self.assertTrue(all(row['outcome'] == 'blocked' for row in evaluate(False, True, False)))

    def test_enabled_qr_and_acl_do_not_prove_an_aap_session(self):
        qr = evaluate(True, True)[-1]
        self.assertEqual(qr['failed_gates'], [])
        self.assertEqual(qr['outcome'], 'unverified')
        self.assertIn('same-phone WPP and full AAP session established', qr['unknown_gates'])

    def test_denial_dominates_unobserved_component_state(self):
        result = outcome('example', [Gate('runtime enabled', None, 'manifest'), Gate('caller signed', False, 'smali')])
        self.assertEqual(result['outcome'], 'blocked')


if __name__ == '__main__':
    unittest.main()

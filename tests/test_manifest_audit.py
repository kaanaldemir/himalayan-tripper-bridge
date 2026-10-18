import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from manifest_audit import audit, TARGETS


class ManifestAuditTest(unittest.TestCase):
    def document(self, body):
        return ('<manifest xmlns:android="http://schemas.android.com/apk/res/android" '
                'package="com.google.android.projection.gearhead">'
                '<application>' + body + '</application></manifest>')

    def test_disabled_receiver_is_not_treated_as_available(self):
        row = audit(self.document(f'<receiver android:name="{TARGETS[0]}" '
                                 'android:enabled="false" android:exported="true"/>'))["components"][0]
        self.assertEqual(row["declared_enabled"], "false")
        self.assertEqual(row["declared_exported"], "true")

    def test_missing_flags_remain_unspecified(self):
        row = audit(self.document(f'<activity android:name="{TARGETS[1]}"/>'))["components"][0]
        self.assertIsNone(row["declared_enabled"])
        self.assertIsNone(row["declared_exported"])

    def test_private_activity_and_resource_flags_are_preserved(self):
        row = audit(self.document(f'<activity android:name="{TARGETS[1]}" '
                                 'android:enabled="@bool/enabled" android:exported="false"/>'))["components"][0]
        self.assertEqual(row["declared_enabled"], "@bool/enabled")
        self.assertEqual(row["declared_exported"], "false")

    def test_actions_are_deduplicated_and_unrelated_components_ignored(self):
        row = audit(self.document(f'<receiver android:name="{TARGETS[0]}">'
                                 '<intent-filter><action android:name="start"/>'
                                 '<action android:name="start"/></intent-filter></receiver>'
                                 '<receiver android:name="other.Receiver"/>'))
        self.assertEqual(len(row["components"]), 1)
        self.assertEqual(row["components"][0]["actions"], ["start"])

    def test_external_entities_are_rejected(self):
        with self.assertRaises(ValueError):
            audit('<!DOCTYPE manifest SYSTEM "file:///unread"><manifest/>')


if __name__ == "__main__":
    unittest.main()

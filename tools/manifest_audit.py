"""Audit declarations in an already-decoded AndroidManifest.xml; never infer runtime state."""
import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

ANDROID = "{http://schemas.android.com/apk/res/android}"
TARGETS = (
    "com.google.android.apps.auto.wireless.setup.receiver.WirelessStartupReceiver",
    "com.google.android.apps.auto.wireless.setup.service.impl.WirelessStartupActivity",
    "com.google.android.apps.auto.wireless.bluetooth.WifiBluetoothReceiver",
    "com.google.android.apps.auto.wireless.deeplink.DeepLinkResolver",
    "com.google.android.apps.auto.wireless.setup.service.impl.WirelessSetupSharedService",
    "com.google.android.apps.auto.carservice.gmscorecompat.FirstActivityImpl",
    "com.royalenfield.reprime.ui.home.navigation.service.REForeGroundService",
)


def audit(xml_text):
    # ElementTree does not resolve external entities. Reject DTDs as unnecessary input.
    if "<!DOCTYPE" in xml_text.upper():
        raise ValueError("DTD declarations are not supported")
    root = ET.fromstring(xml_text)
    app = root.find("application")
    sdk = root.find("uses-sdk")
    components = []
    package = root.get("package", "")
    if app is not None:
        for item in app:
            if item.tag not in {"activity", "activity-alias", "service", "receiver", "provider"}:
                continue
            name = item.get(ANDROID + "name", "")
            if name.startswith("."):
                name = package + name
            elif name and "." not in name:
                name = package + "." + name
            if name not in TARGETS:
                continue
            components.append({
                "name": name,
                "kind": item.tag,
                "declared_enabled": item.get(ANDROID + "enabled"),
                "declared_exported": item.get(ANDROID + "exported"),
                "declared_permission": item.get(ANDROID + "permission"),
                "actions": sorted({a.get(ANDROID + "name") for f in item.findall("intent-filter")
                                   for a in f.findall("action") if a.get(ANDROID + "name")}),
            })
    return {
        "package": package,
        "version_code": root.get(ANDROID + "versionCode"),
        "version_name": root.get(ANDROID + "versionName"),
        "min_sdk": sdk.get(ANDROID + "minSdkVersion") if sdk is not None else None,
        "target_sdk": sdk.get(ANDROID + "targetSdkVersion") if sdk is not None else None,
        "components": sorted(components, key=lambda c: c["name"]),
        "scope": "Manifest declarations only; runtime component overrides and feature flags are unknown.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifests", type=Path, nargs="+")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = [audit(p.read_text(encoding="utf-8")) for p in args.manifests]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote declaration observations for {len(result)} APK(s) to {args.out}")


if __name__ == "__main__":
    main()

"""Reconstructed startup guards for an independently signed, ordinary app.

Source-derived model of inspected AA 17.8, not Android Auto execution. A
candidate outcome means a route reaches unverified protocol work, not success.
"""
import argparse
from dataclasses import dataclass
import json


@dataclass(frozen=True)
class Gate:
    name: str
    value: object
    evidence: str


def outcome(name, gates):
    failed = [gate.name for gate in gates if gate.value is False]
    unknown = [gate.name for gate in gates if gate.value is None]
    return {
        'route': name,
        'outcome': 'blocked' if failed else 'unverified' if unknown else 'candidate',
        'failed_gates': failed,
        'unknown_gates': unknown,
        'evidence': [gate.evidence for gate in gates],
    }


def evaluate(qr_enabled=None, acl_present=None, legacy_receiver_enabled=None):
    # The actor is our independently signed app, with no root, Google signing
    # keys, shared Google UID, developer server, or external USB receiver.
    return [
        outcome('Legacy WirelessStartupReceiver', [
            Gate('receiver effectively enabled by Android Auto/system', legacy_receiver_enabled,
                 'manifest disabled; no named enabling reference found in DEX instruction scan; effective runtime state unmeasured'),
            Gate('complete same-phone AAP session established', None, 'receiver forwards to internal startup activity; not executed'),
        ]),
        outcome('FirstActivity WIFI_ACTION_BRIDGE', [
            Gate('caller is Google-signed', False, 'FirstActivityImpl.onCreate / spt.b'),
        ]),
        outcome('FirstActivity RESTART or legacy START_DUPLEX', [
            Gate('zero-party callback has sender UID', False, 'FirstActivityImpl.E / shu.e'),
        ]),
        outcome('START_DUPLEX service handshake', [
            Gate('same UID or Google-signed allowlisted caller', False, 'slr.b / shg.e'),
        ]),
        outcome('WirelessSetupSharedService Binder', [
            Gate('same UID or Google-signed allowlisted caller', False, 'WirelessSetupSharedService.b / pfs'),
        ]),
        outcome('GearheadCarStartupService handoff Binder', [
            # This guard is in the actual handoff delegate and remains when
            # jtd.onTransact's separate feature-controlled proxy check is off.
            Gate('same UID or Google-signed allowed package', False, 'jtc.d/r/k/l / jnw.a / jnu.a / iog case 8'),
        ]),
        outcome('USB accessory startup', [
            Gate('real external USB transport available', False, 'slh.a/b/c / UsbConnectionHelper'),
        ]),
        outcome('Developer head-unit server', [
            Gate('developer-server setup permitted', False, 'Open Headunit SelfLauncherV17_4'),
        ]),
        outcome('QR provisioned WPP/TCP', [
            Gate('Google-controlled QR feature enabled', qr_enabled, 'DeepLinkResolver.onCreate / acth'),
            Gate('genuine Bluetooth ACL presence available', acl_present, 'WirelessSetupSharedService.onStartCommand / ldk.h / phc'),
            Gate('same-phone WPP and full AAP session established', None, 'not executed; numeric-IP validation alone is insufficient'),
        ]),
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--qr-enabled', action='store_true')
    group.add_argument('--qr-disabled', action='store_true')
    legacy = parser.add_mutually_exclusive_group()
    legacy.add_argument('--legacy-receiver-enabled', action='store_true')
    legacy.add_argument('--legacy-receiver-disabled', action='store_true')
    parser.add_argument('--acl-present', action='store_true')
    args = parser.parse_args()
    qr = True if args.qr_enabled else False if args.qr_disabled else None
    receiver = True if args.legacy_receiver_enabled else False if args.legacy_receiver_disabled else None
    print(json.dumps({
        'scope': 'Static guard model; switches are hypothetical inputs, not measured phone state.',
        'routes': evaluate(qr, True if args.acl_present else None, receiver),
    }, indent=2))


if __name__ == '__main__':
    main()

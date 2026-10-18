# Android Auto bootstrap: code beyond the manifest

Applies to the exact Android Auto 17.8.663874-release base APK in [artifacts.json](../evidence/artifacts.json). This is a reconstruction of relevant DEX behavior, not recovered original source, a runtime trace, or a proof about every Android Auto release.

The actor is an ordinary, independently signed application on the same phone. It has neither Google's app-signing identity nor Android Auto's UID. User consent to a companion app does not give it either identity.

## What changed after deeper inspection

The initial manifest-only reasoning was incomplete. `ComponentInitReceiver.b()` calls its helper `c()` to enable `FirstActivityImpl` for ordinary Android R+ profiles; work/private-profile conditions can disable it. The critical branches were also checked in smali because JADX emits warnings and duplicated branches for the Java interpretation.

Enabling the activity is therefore not the decisive question. The activity's action-specific caller checks are.

| Route | Reconstructed path | Gate for our independently signed app |
| --- | --- | --- |
| Direct Wi-Fi intent | `FirstActivityImpl.onCreate`, action `com.google.android.gms.car.WIFI_ACTION_BRIDGE` -> `getCallingPackage()` -> `spt.a(context).b(package)` | Requires an identified Google-signed calling package. Missing or untrusted caller finishes the activity. |
| Restart / legacy duplex | `FirstActivityImpl.E(intent)` -> `0p_checker` BinderParcel -> checker callback -> `shu.e()` -> `uwq`/`lzf` -> activity continuation | The callback tests `Binder.getCallingUid() == Process.myUid()`. Implementing a Binder in our process does not make our UID Android Auto's UID. |
| Newer duplex handshake | `slr.b()` -> `service_handshake` -> callback `shg.e()` | Same UID, or a Google-signed caller in the configured allowed-package list. |
| Exported wireless setup Binder | `WirelessSetupSharedService.onBind()` -> `pfs` methods -> service `b()` | Same UID, or package allowlist **and** Google's signing check. The exported declaration is not authorization. |
| Exported startup/handoff Binder | `GearheadCarStartupService.onBind()` -> `jtd` / `sbu` transaction 20 -> `jtc.d()` -> `jnw.a(context)` -> `jnu.a(context)` | Same UID or Google-signed package in the instantiated allowlist. Checked before host/port is consumed. |
| USB accessory | First activity USB branches -> `slh` / `UsbConnectionHelper` | Real accessory/file-descriptor transport is required. Sending an action name does not create it. Extra hardware is outside this project's constraints. |
| Developer server | Open Headunit `SelfLauncherV17_4` -> `127.0.0.1:5277` | Requires the user to enable Android Auto's developer head-unit server. Excluded by the requested setup. |

### The handoff service has two different guards

`jtd.onTransact()` has a feature-controlled proxy signature check. Its `GearheadCarService__startup_proxy_signature_check_enabled` flag has a compiled default of **false**. Treating that flag as an always-enforced barrier would be wrong.

The actual handoff implementation is independently protected:

```text
IStartup transaction 20
  sbu.dd(...) -> jtd.d(...) -> jtc.d(...)
    -> jtc.b (new jnw()).a(context)
      -> lazy jnu from iog.eo(), case 8
        -> permitted same UID, OR Google-signed AND package allowed
    -> only after validation: PARAM_HOST_ADDRESS / PARAM_SERVICE_PORT
```

The case-8 allowlist contains `com.google.android.projection.gearhead` and `com.google.android.gms`, with same-UID calls allowed. `jnu` caches accepted UIDs after validation. This is not a public host/port API for independent apps. Other meaningful `jtc` operations, including startup registration, also call the guard. Critical `jtc`/`jnw`/`jtd` paths were examined in smali; `jnu` and the constructor case were also emitted as smali for review.

### Legacy disabled receiver

`WirelessStartupReceiver.b()` accepts a numeric `ip_address` and valid `projection_port`, then starts private `WirelessStartupActivity` from Android Auto's own process. If effectively enabled, this is a distinct route into the trusted internal flow; the caller checks on *direct* activity launches must not be incorrectly applied to the originating independent app here.

Its manifest default is disabled. Raw DEX searches found zero type-instruction references to `WirelessStartupReceiver`, and one string-instruction match (its own diagnostic name). We inspected component initialization and the component-enable callers relevant to projection; no ordinary public enabling mechanism was identified. This search does not exhaust reflective, resource-driven, native or privileged external behavior. Effective PackageManager state on a real installation remains unknown. Enabling it through root or shell is not an allowed solution.

## QR/WPP is a separate, conditional path

The exported `DeepLinkResolver` is designed to receive a user-approved provisioning link. It first checks `DeepLink__enabled`, compiled default false, with actual Google-delivered configuration unknown. Its confirmation handler stores Wi-Fi credentials and WPP endpoint against a Bluetooth device.

The traced setup then does the following:

```text
QR payload + Android Auto consent
  -> jpi.onClick case 13 -> pds datastore
  -> WifiBluetoothReceiver / WirelessSetupSharedService.onStartCommand
  -> ldk.f -> phc.fO -> ldk.h(pha state)
  -> WPP/TCP setup -> pjg.a -> jgd.a(Network)
  -> TCP dial to configured endpoint
  -> TLS server mode, client certificate required
  -> WPP negotiation -> Wi-Fi/AAP startup
```

The stored WPP configuration can waive HFP/A2DP presence, but `phc` still accepts only connected states `phe.c` or `phe.d`. `pgy` updates `pha` from Bluetooth events; naming a MAC address in the link does not by itself mark it connected. Depending on configuration, bonding can also be required. Whether a stock dash supplies suitable genuine presence has not been established. We did not pretend that a headset or an invented MAC solves that requirement for every rider.

`pjg.a()` obtains a socket from the selected Android `Network` via `jgd.a()`. This matters: a successful desktop localhost socket does not establish that Android Auto's requested Wi-Fi network, routing and permissions allow the same operation on a phone. The parser's numeric-IP validation alone does not settle this.

### The certificate question is narrower now

`pjg.a()` sets `useClientMode=false` and `needClientAuth=true`. `jdr.d()` initializes TLS 1.2, while `sae` creates a normal trust manager using an embedded public automotive CA. A random self-signed receiver certificate cannot be assumed to pass that check.

We extracted **only the public CA certificate** for comparison and supplied the public receiver certificate from the pinned Open Headunit source to an independent JDK probe. Its signature, validity and client trust passed. We then performed a real desktop loopback TLS 1.2 exchange with Open Headunit's supplied receiver key/certificate and a separately generated synthetic phone-side identity. The dialer played TLS server, required the receiver certificate, verified it against that CA, and exchanged synthetic bytes.

| Public certificate | SHA-256 of DER |
| --- | --- |
| Automotive trust anchor | `49e52efc13ad2ed09f204c3b10698bd84bb7105f510558aa14b8119a5c4ad17f` |
| Pinned Open Headunit receiver | `e323cc6dd52d1f2a280360a0e92efa04ab3664dd68fab3dd187f03d663feed6d` |

The receiver certificate's `notAfter` is 2044-07-07T22:49:18Z. The probe used no APK private key, and the repository distributes no key or certificate bundle. Upstream licensing and provenance still apply if material is incorporated into a product. JDK trust success is not a measurement of Android's provider behavior; the loopback server was synthetic, not Android Auto.

This gives a concrete implementation direction for an eligible QR session. It does not remove the feature, Bluetooth-presence, same-phone routing or complete-session requirements.

## Executable guard model and its limits

`bootstrap_model.py` records these routes with three-valued gates: true, false and unknown. It never reports a complete projection success. Flags supplied to this script are hypothetical scenario inputs, not commands that change a phone.

```sh
python bootstrap_model.py
python bootstrap_model.py --qr-disabled --legacy-receiver-disabled
python bootstrap_model.py --qr-enabled --acl-present
```

In a scenario with QR off and the legacy receiver disabled, none of the **audited routes** is available under the stated constraints. Unknown runtime configuration is kept unknown. That result does not prove that an uninspected component or future public mechanism cannot exist, nor that every phone currently has both gates disabled.

The product requirement remains unmet. The new evidence explains why copying the app's architecture or adding an overlay does not produce a universally launchable Android Auto receiver. A further solution must identify an ordinary, available entry point and complete WPP/AAP through it; it cannot silently replace that requirement with root, a developer server, or a Google-signed identity.

# Findings, 19 October 2026

## Scope and result

The intended product is a phone-side bridge for **the phone's full Android Auto session**, including its app interface, displayed on the existing Himalayan 450 Tripper Dash while the phone is locked. Constraints: ordinary Android permissions and pairing, no root, no ADB/Shizuku/modified APKs, no extra computer or dongle, no bike flashing or special bike configuration. Ordinary first pairing must be distinguished from changing how the bike operates.

**We have not established a complete solution under those constraints.** The dash output is understood well enough to design a bridge. Starting a full Android Auto receiver session on the same phone is the unresolved dependency. QR/WPP provisioning is a plausible research direction, not a demonstrated solution.

The evidence below comes from static inspection of two downloaded APKs and pinned open-source implementations. No Android process was run, no head-unit server was enabled, no motorcycle was connected, and no firmware image was acquired or disassembled. Server-side feature configuration and runtime component overrides were not observed.

## 1. What the Royal Enfield app actually does

**Direct APK evidence: Royal Enfield 10.1.23(45), version code 193.**

| Symbol in this version | Observation |
| --- | --- |
| `bluconnect.sbk` | Constants include width 526, height 300, frame rates 4 and 2, intervals 250 and 500 ms, and `video/avc`. |
| `NavigationFragment.D7()` | Creates the AVC media configuration using remote/configuration-supplied bitrate and frame rate, width 526, height 300, and a one-second keyframe interval. |
| `NavigationFragment.m.run()` | Periodically asks the navigation component for a bitmap through `k18.u0(...)`, then reschedules at 250 or 500 ms. |
| `NavigationFragment.r(Bitmap)` and `J8(...)` | Receives a map bitmap and scales it to 526 x 300. |
| `NavigationFragment.g0.run()` | Submits the current bitmap only while boolean `U2` is true, then reschedules. |
| `NavigationFragment.k9(Bitmap)` | Sends the bitmap to `w9f.c(...)` and announces projection frames through the K1G control path. |
| `bluconnect.w9f.c(...)`, `bluconnect.gub.g(...)` | Hands the bitmap to an encoder surface and draws it with software or hardware Canvas. The encoder uses MediaCodec. |
| `NavigationFragment.onStop()` | Calls `g9()`, sets `U2=false`, sets `I2=false`, sends `w2c.x`, and then calls the superclass. |
| `NavigationFragment.g9()` | Removes the snapshot runnable from its handler and resets its counter. |
| `bluconnect.w2c.x` | The projection-off command containing TLV `06 05 00 01 AA`. |
| Manifest | `REForeGroundService` is private and declares `connectedDevice`. No MediaProjection foreground-service declaration was found. |

`NavigationFragment.onPause()` also calls the timer-stop path outside picture-in-picture. `onResume()` re-enables frame submission and restarts relevant behavior. The fragment contains explicit screen-on/off receivers and wake-lock handling.

**Conclusion:** the inspected app ties map snapshot production and projection state to its UI lifecycle. It does not merely lack a permission that an overlay can grant. A companion cannot normally change another app's private fragment lifecycle or use its private service as a supported public map source.

This corrects the common claim that the dash inherently requires the phone display to remain lit. It also corrects an overly broad explanation that assumes the RE app necessarily uses Android MediaProjection. The observed pipeline is bitmap-to-encoder. Android's screen-capture lock rules matter if someone proposes a screen-mirroring workaround, but are not the demonstrated root cause here.

## 2. What the stock dash accepts

**Upstream implementation evidence**, corroborated in part by current APK constants:

- Wi-Fi network advertised by the dash, usually `RE_*`.
- K1G control TX: local UDP 2000 to broadcast `192.168.1.255:2000`.
- Control RX: UDP 2002, listening before the initial control burst.
- Public-key exchange and an RSA-encrypted SSID plus random session key; the reference implementations expect 128-byte RSA ciphertext.
- Ordered authentication, navigation/projection entry, status heartbeats, and projection heartbeats.
- H.264/RTP to `192.168.1.1:5000`, with a 90 kHz RTP clock and payload type 96 in the reference implementations.
- Decoder notifications and button events require acknowledgements.

See the pinned [better-dash implementation](https://github.com/norbertFeron/better-dash/blob/e32d885372e8f18b49c3bf73c8add8692d377b5b/tripper_app_like_nav.py) and [OpenDash protocol notes](https://github.com/jayvadolkar/open-dash-re/blob/ed26faf78449a42eb9fc5934957e3e8feaa9839a/docs/PROTOCOL_FREEZE.md). They contain firmware-specific assumptions; they do not establish all firmware compatibility.

The dash does not need to understand Android Auto if the phone terminates Android Auto's receiver protocol and converts its video into the existing dash format. It still needs the proper K1G session, codec parameters, input acknowledgements, and timing.

**Ordinary pairing is not zero interaction:** Royal Enfield's [official pairing instructions](https://www.royalenfield.com/in/en/tripper-dash/) require generating the dash SSID with the joystick. better-dash also documents Digital mode and enabling the existing Wi-Fi function. We have not established a way to remove those requirements on every stock firmware. No claim of “zero bike configuration” beyond normal pairing is justified yet.

## 3. Why existing Android Auto self-mode is insufficient

**Direct APK evidence: Android Auto 17.8.663874-release, version code 178663874.**

| Entry point | Declaration / behavior | Implication |
| --- | --- | --- |
| `WirelessStartupActivity` | `exported=false` | A normal third-party app cannot simply launch this activity as legacy self-mode code did. |
| `WirelessStartupReceiver` | `enabled=false`, `exported=true` | Being exported does not make a disabled receiver callable. Its method can forward host/port to the private activity, but the disabled declaration blocks relying on that entry point by default. |
| `FirstActivityImpl` | `enabled=false`, `exported=true` | Another declared-disabled entry point is not a reliable public launch API. |
| `WifiBluetoothReceiver` | Enabled and exported | Triggers the ordinary wireless device flow, not a generic public “project to this arbitrary socket” API. |

These are **manifest defaults**, not measurements of a device's effective PackageManager state. Android Auto or another privileged component may change its own component state. That uncertainty prevents treating a static declaration as a universal runtime verdict.

[Open Headunit's current self-launcher](https://github.com/andreknieriem/open-headunit/blob/afe6a534811970893b7a8f745617cd84bd04a021/app/src/main/java/com/andrerinas/openheadunit/connection/self/launchers/SelfLauncherV17_4.kt) connects to `127.0.0.1:5277` and asks the user to start Android Auto's developer head-unit server. Its older launcher uses internal explicit intents and reflective network objects. Its [README](https://github.com/andreknieriem/open-headunit/blob/afe6a534811970893b7a8f745617cd84bd04a021/README.md) also documents a root workaround.

Those implementations are useful protocol references, but do not satisfy this project's phone-setup requirements. Adding Car App Library declarations only makes an app usable *inside* Android Auto; it does not create a receiver for the full interface. Google's [Android Auto overview](https://developer.android.com/training/cars/platforms/android-auto) describes that distinction.

## 4. The strongest remaining candidate: QR provisioning and WPP/TCP

The inspected APK declares `com.google.android.apps.auto.wireless.deeplink.DeepLinkResolver` exported. It accepts Android Auto projection links, including `https://androidauto.com/projection/...`, and presents its own user confirmation.

Static trace:

1. `DeepLinkResolver.onCreate()` first checks `actf.c()`.
2. `actf.c()` reads `acth`, whose flag `DeepLink__enabled` has a **compiled default of false**. Actual server-delivered configuration is unknown.
3. If enabled, the resolver decodes a protobuf payload and validates SSID, passkey, BSSID, Bluetooth address, and a numeric IPv4 WPP endpoint.
4. The confirmation handler, `jpi.onClick()` case 13 in this build, saves network credentials and the WPP/TCP endpoint keyed to that Bluetooth device, then sends the WPP startup action.
5. `WirelessSetupSharedService.onStartCommand()` checks stored WPP configuration and head-unit presence. For the WPP path, it can avoid requiring HFP/A2DP, but still waits for Bluetooth ACL presence.
6. `pha.toString()` names the relevant state fields (`aclConnected`, `hfpConnected`, `a2dpConnected`, `isBonded`). `ldk.h(...)` and `phc.fO(...)` select the acceptable presence state. The service reports an ACL-related failure when this gate fails in the WPP case.

This is more promising than launching a private activity. A candidate bridge would provision the bike's normal Wi-Fi and a **receiver endpoint on the same phone**, then translate the resulting Android Auto session into K1G/RTP.

**Unresolved gates:**

- Is this pairing feature available on the target population without changing Google-controlled flags?
- Does the stock Tripper's normal connection supply the Bluetooth presence state Android Auto expects, without pairing unrelated hardware or inventing a device identity?
- Does the complete WPP/Wi-Fi connection sequence accept a same-phone endpoint such as loopback or the phone's address on the dash network?
- Does Android Auto preserve a usable no-internet dash Wi-Fi connection while its app traffic uses mobile data?
- Can the receiver maintain full projection, audio and microphone behavior when locked across current Android versions?

Acceptance of an IP string at the resolver is **not** proof that the networking state machine, TLS handshake and session startup will accept it. A default-off flag is also **not** proof that no real user has the feature. Neither side should be overstated.

Open Headunit already has [QR provisioning code](https://github.com/andreknieriem/open-headunit/blob/afe6a534811970893b7a8f745617cd84bd04a021/app/src/main/java/com/andrerinas/openheadunit/connection/wifi/modes/nativeaa/ProjectionDeepLink.kt) and a [WPP TCP receiver](https://github.com/andreknieriem/open-headunit/blob/afe6a534811970893b7a8f745617cd84bd04a021/app/src/main/java/com/andrerinas/openheadunit/connection/wifi/modes/nativeaa/WppTcpServer.kt). Its implementation concerns separate receiver devices; that is not proof of same-phone operation. It negotiates WPP 4.2 to avoid a 4.1 manufacturer allowlist, while sending its configured identity. We should not copy certificate/trust handling or introduce impersonation as an unnoticed implementation detail.

## 5. Firmware evidence

The downloaded app package did not supply an identified dash firmware image. A filename inventory found `DebugProbesKt.bin`, which is a Kotlin debugging resource, not evidence of dashboard firmware. Native split libraries were present; no firmware extraction from packed/native content was attempted.

The APK contains updater code and remote metadata models. `bluconnect.tw6` is the Firestore service; its `O(...)` path reads `RE_FOTA_FULL`. Its `e0(...)` method is the `getReFotaTripper` coroutine. `bluconnect.mkf` includes fields named `firmwareMappingUrl`, `firmwareUrl`, and `firmwareVersion`. Additional DEX strings include `otap/otap/firmwaredownload`.

These identify retrieval mechanisms, not an acquired firmware image. No protected service was queried using extracted app credentials, and no binary firmware version was verified. Consequently, we cannot claim that firmware has been reverse-engineered or that all dashboard variants have identical limits.

Firmware is not the first dependency to change: changing the dash violates the requested product constraints. The existing stock video path already supplies the output channel. The next decisive unknown is Android Auto startup on an ordinary phone.

## 6. What can and cannot be concluded today

| Claim | Evidence status |
| --- | --- |
| A replacement app can generate video without the phone display being on | Supported by Android's rendering/codec model and existing implementations; not measured here. |
| The inspected RE app stops its projection pipeline with its fragment | Direct APK observation, with the critical `onStop()` path also checked in smali. |
| A rootless, no-developer-settings Android Auto bridge works on the stock Himalayan | **Not established.** |
| Full Android Auto is inherently impossible on this dash | **Not established.** A translating receiver is architecturally possible; bootstrap is unresolved. |
| A QR link alone solves it for everyone | **Not supported.** Feature, device-presence and same-phone session gates remain. |
| Android Auto support implies CarPlay support | **False inference.** CarPlay needs a separate receiver/platform investigation. |

The useful outcome is a precise problem statement: **implementing K1G output is not the main obstacle; obtaining a complete, supported same-phone Android Auto receiver session under the setup constraints is.**

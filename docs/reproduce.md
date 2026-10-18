# Reproduce the static inspection

## Inputs and boundaries

Use a desktop with a full JDK 17+ and Python 3.10+. The original run used Microsoft OpenJDK 21 and JADX 1.5.6 through the SHA-pinned `jadx-headless-mcp` 0.7.1 JAR recommended by REA. No APK is executed. No phone, root, emulator, account credentials or bike connection is needed for this static work.

Obtain the app packages independently. The original run downloaded mirror-distributed XAPK bundles for:

- `com.royalenfield.reprime`, 10.1.23(45), version code 193.
- `com.google.android.projection.gearhead`, 17.8.663874-release, version code 178663874.

See [artifacts.json](../evidence/artifacts.json) for URLs, hashes, signer certificates and the limits of that provenance. A mirror's “verified” label is not our trust anchor. The verifier establishes signature integrity and reports certificate hashes; it does not establish publisher identity by itself.

For XAPK input, inspect its ZIP entry list first and extract the base APK to ignored `.local/inputs/`. Do not install the bundle or run an installer. The inspected base names were `com.royalenfield.reprime.apk` and `com.google.android.projection.gearhead.apk`. ABI/resource splits were not decompiled. The firmware-file inventory covered the RE base package; it was not an exhaustive search of packed native resources.

## Prepare pinned tools

PowerShell, from the repository root:

```powershell
./tools/prepare-tools.ps1
```

The script downloads two JARs into `.local/tools/`, checks fixed SHA-256 digests, and makes no global installation or configuration change. Put your existing JDK's `bin` on PATH. The tool source files can also be used on Linux or macOS after fetching the same pinned JARs from the URLs in that script.

## Verify the APKs

```powershell
java --class-path .local/tools/apksig.jar tools/ApkVerify.java .local/inputs/com.royalenfield.reprime.apk .local/inputs/com.google.android.projection.gearhead.apk
```

In the original run both base APKs passed APK Signature Scheme v3 verification with no verifier errors. Preserve the reported signer digests separately from file hashes. A different APK version or split can have a different file hash without implying tampering.

## Decode manifests and inspect targeted classes

```powershell
java -Xmx2g --class-path .local/tools/jadx-headless.jar tools/ApkInspector.java .local/inputs/com.royalenfield.reprime.apk .local/re '@manifest' com.royalenfield.reprime.ui.home.navigation.fragment.NavigationFragment bluconnect.sbk bluconnect.w9f bluconnect.gub bluconnect.w2c

java -Xmx2g --class-path .local/tools/jadx-headless.jar tools/ApkInspector.java .local/inputs/com.google.android.projection.gearhead.apk .local/aa '@manifest' com.google.android.apps.auto.wireless.setup.receiver.WirelessStartupReceiver com.google.android.apps.auto.wireless.setup.service.impl.WirelessStartupActivity com.google.android.apps.auto.wireless.deeplink.DeepLinkResolver com.google.android.apps.auto.wireless.setup.service.impl.WirelessSetupSharedService actf acth jpi pha ldk phc
```

PowerShell has no backslash line continuation; the blank lines separate independent commands. Each command above is one line.

The helper looks up raw class nodes and emits only selected classes. Avoid traversing `JavaClass.getInnerClasses()` for every class: on this engine it can unexpectedly materialize code throughout a large APK. REA's metadata bridge documents the same distinction between raw nodes and Java API getters. This helper uses the engine directly, rather than registering REA as a persistent MCP server or modifying Codex settings.

The Java source is an interpretation of DEX. Decompiled methods can contain incorrect control flow or omitted bodies. To check a critical method in smali:

```powershell
java -Xmx2g --class-path .local/tools/jadx-headless.jar tools/ApkInspector.java .local/inputs/com.royalenfield.reprime.apk .local/re '@smali:com.royalenfield.reprime.ui.home.navigation.fragment.NavigationFragment' '@smali:bluconnect.tw6'
```

Look for `onStop()V` in the first class. The inspected method invokes `g9()`, writes false to `U2` and `I2`, loads the projection-off packet string (represented as `w2c.x` in the Java output), and invokes `m9(String)` before `super.onStop()`.

For the updater, inspect `bluconnect.tw6`, `bluconnect.uw6`, `bluconnect.mkf` and the `getReFotaTripper` coroutine. Some Java bodies are omitted, which is why the smali mode matters. Finding metadata/download code is not obtaining the firmware.

## Follow callers and initialization beyond declarations

The deeper Android Auto pass inspected these version-specific symbols:

```powershell
java -Xmx2g --class-path .local/tools/jadx-headless.jar tools/ApkInspector.java .local/inputs/com.google.android.projection.gearhead.apk .local/aa com.google.android.apps.auto.carservice.gmscorecompat.ComponentInitReceiver com.google.android.gms.carsetup.FirstActivityImpl slr shu shg pfs jtd jtc jnw jnu iog acur pjg jgd jdr sae pgy

java -Xmx2g --class-path .local/tools/jadx-headless.jar tools/ApkInspector.java .local/inputs/com.google.android.projection.gearhead.apk .local/aa '@smali:com.google.android.apps.auto.carservice.gmscorecompat.ComponentInitReceiver' '@smali:com.google.android.gms.carsetup.FirstActivityImpl' '@smali:shu' '@smali:shg' '@smali:jtc' '@smali:jnw' '@smali:jnu' '@smali:iog' '@smali:pjg'
```

The helper can scan instruction references without decompiling every method:

```powershell
java -Xmx2g --class-path .local/tools/jadx-headless.jar tools/ApkInspector.java .local/inputs/com.google.android.projection.gearhead.apk .local/aa '@find-string:full_loopback_protections_enabled' '@find-type:WirelessStartupReceiver' '@find-call:Ljava/net/Socket;->connect' '@find-call:Landroid/content/pm/PackageManager;->setComponentEnabledSetting'

java -Xmx2g --class-path .local/tools/jadx-headless.jar tools/ApkInspector.java .local/inputs/com.royalenfield.reprime.apk .local/re '@find-string:192.168.1.1' '@find-string:RSA/ECB/PKCS1Padding' bluconnect.cyb bluconnect.a78 bluconnect.omf
```

Queries are case-sensitive substring matches. Method queries use a DEX owner descriptor followed by `->` and a method name; include the full descriptor to avoid matching unrelated owners. Call queries omit argument signatures, so overloads can match together. `@find-type` scans **TYPE_REF instructions**, not every type mention in signatures, annotations, resources or strings. `@find-string` scans STRING_REF instructions, not all possible runtime string construction. Output includes the caller class, method and DEX code-unit offset; matched raw values are deliberately omitted. At most 200 sites are printed and the total count is reported. These are reference searches, not exhaustive dynamic call graphs.

See [android-auto-bootstrap.md](android-auto-bootstrap.md) for the actual decision paths and [virtual-validation.md](virtual-validation.md) for the executable independent reconstruction. Keep `jdr`/`sae` outputs private, since cryptographic/configuration material can occur alongside the public certificate we compared. The public probes do not require decrypting or using any APK private key.

## Produce a small declaration report

```powershell
python tools/manifest_audit.py .local/re/AndroidManifest.xml .local/aa/AndroidManifest.xml --out .local/manifest-observations.json
python -m unittest discover -s tests -v
```

The audit selects only named projection components. It preserves unspecified and resource-valued attributes, rather than treating them as boolean truth or inferring effective runtime state. It does not read device PackageManager overrides or Google feature flags.

## Before sharing results

Keep `.local/` private. It can contain proprietary code, device information and app configuration. Publish original analysis, artifact hashes, minimal identifiers, and reproducible commands. Do not commit input APKs, firmware images, application keys, signing material, account tokens, or decompiled source dumps. Nothing in this workflow uploads inputs to an analysis service.

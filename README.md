# Himalayan Tripper Bridge

Research toward **full Android Auto on the stock Royal Enfield Himalayan 450 Tripper Dash**, with the phone locked, no root, no phone modifications, no extra hardware, and no bike firmware changes.

**Status: feasibility investigation. There is no working Android Auto bridge or installable app in this repository yet.** This repository publishes the findings and tools, not a claim that the problem is solved.

## What we established

1. **The dash video path is usable.** Existing implementations speak its K1G control protocol and send H.264/RTP over Wi-Fi. Screen-off rendering does not require mirroring the phone's screen.
2. **The current Royal Enfield Android app explicitly stops its frame loop when its navigation fragment stops.** Direct inspection of version 10.1.23(45) found bitmap snapshots, a MediaCodec encoder, and an `onStop()` path that cancels snapshots, disables frame submission, and sends projection-off. This is stronger evidence than assuming Android blocks every form of screen-off navigation.
3. **Android Auto startup has actual caller checks, beyond manifest declarations.** Android Auto can enable its exported `FirstActivityImpl` itself. Its direct Wi-Fi path nevertheless verifies Google's app-signing identity; other activity and Binder paths verify UID or a Google-signed package allowlist. Reconstructing this code does not grant an independent app that identity. See the [startup call graph](docs/android-auto-bootstrap.md).
4. **QR provisioning / WPP over TCP remains conditional.** Its feature has a compiled default of off and its setup path waits for genuine Bluetooth presence. We traced the TCP/TLS roles and verified that Open Headunit's public receiver certificate passes the reconstructed trust-anchor check. A desktop TLS exchange using those receiver credentials passed. This removes one uncertainty; it does not demonstrate Android Auto startup on the same phone.
5. **Original transport code now runs against a local synthetic peer.** The repository implements K1G framing, decoder/button ACKs and RTP fragmentation, with a loopback exercise and tests. It does not yet implement a complete authenticated dash session, an H.264 decoder, or an Android Auto receiver.

**Decision: proceed with research on the Android Auto bootstrap; do not ship a claimed universal Android Auto app yet.** A separate map application or notification bridge would not satisfy this project's full Android Auto goal.

## Read the evidence

- [Technical findings and evidence boundaries](docs/findings.md)
- [Android Auto startup guards, call graph and conditional routes](docs/android-auto-bootstrap.md)
- [Executable reconstruction and virtual test boundaries](docs/virtual-validation.md)
- [Proposed architecture and open questions](docs/architecture.md)
- [Reproduction instructions](docs/reproduce.md)
- [Versioned artifacts and source revisions](evidence/artifacts.json)
- [Declaration observations extracted from the inspected APK manifests](evidence/manifest-observations.json)

The findings distinguish direct APK observations, upstream implementation evidence, independent desktop probes, and untested hypotheses. No motorcycle, Android runtime, or firmware image was tested in this investigation.

## Developer tools

The repository contains a targeted JADX inspector with raw instruction-reference searches, an APK signature verifier, manifest auditing, a source-derived startup guard model, and independent wire/cryptographic probes. Inputs and decompiled material stay in ignored `.local/`; proprietary APKs, firmware, credentials and decompiled app sources are not redistributed.

Run the tooling tests with Python 3.10 or newer:

```sh
python -m unittest discover -s tests -v
python tools/virtual_link.py
python bootstrap_model.py
```

See [reproduce.md](docs/reproduce.md) for inspecting the exact APK versions. These are desktop research tools, not requirements for an eventual rider-facing app.

## Existing work

[better-dash](https://github.com/norbertFeron/better-dash), [OpenDash](https://github.com/subtlesayak/open-dash), and [Open Headunit](https://github.com/andreknieriem/open-headunit) already solve important parts of the problem. [REA](https://github.com/morluto/rea) supplied a useful toolchain reference and a pinned JADX engine. Their respective licenses apply to their code; this repository's original tooling is MIT-licensed.

Independent community research. Not affiliated with Royal Enfield, Google, or Apple. Android Auto and CarPlay are separate projection systems; an iPhone screen-off navigation app is not evidence of CarPlay support.

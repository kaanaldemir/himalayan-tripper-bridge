# Himalayan Tripper Bridge

Research toward **full Android Auto on the stock Royal Enfield Himalayan 450 Tripper Dash**, with the phone locked, no root, no phone modifications, no extra hardware, and no bike firmware changes.

**Status: feasibility investigation. There is no working Android Auto bridge or installable app in this repository yet.** This repository publishes the findings and tools, not a claim that the problem is solved.

## What we established

1. **The dash video path is usable.** Existing implementations speak its K1G control protocol and send H.264/RTP over Wi-Fi. Screen-off rendering does not require mirroring the phone's screen.
2. **The current Royal Enfield Android app explicitly stops its frame loop when its navigation fragment stops.** Direct inspection of version 10.1.23(45) found bitmap snapshots, a MediaCodec encoder, and an `onStop()` path that cancels snapshots, disables frame submission, and sends projection-off. This is stronger evidence than assuming Android blocks every form of screen-off navigation.
3. **The usual same-phone Android Auto launch tricks do not meet the requirements.** In the inspected Android Auto 17.8 APK, the startup activity is not exported and the legacy startup receiver is disabled. Open Headunit's current self-mode therefore uses Android Auto's developer head-unit server.
4. **QR provisioning / WPP over TCP is a candidate worth investigating.** The APK has an exported pairing resolver that stores a receiver's Wi-Fi credentials and TCP endpoint after user confirmation. However, it is feature-flag controlled and the subsequent flow checks Bluetooth presence. Same-phone operation with the stock bike has not been established.

**Decision: proceed with research on the Android Auto bootstrap; do not ship a claimed universal Android Auto app yet.** A separate map application or notification bridge would not satisfy this project's full Android Auto goal.

## Read the evidence

- [Technical findings and evidence boundaries](docs/findings.md)
- [Proposed architecture and open questions](docs/architecture.md)
- [Reproduction instructions](docs/reproduce.md)
- [Versioned artifacts and source revisions](evidence/artifacts.json)
- [Declaration observations extracted from the inspected APK manifests](evidence/manifest-observations.json)

The findings distinguish direct APK observations, upstream implementation evidence, and untested hypotheses. No motorcycle, Android runtime, or firmware image was tested in this investigation.

## Developer tools

The repository contains a targeted JADX inspector, an APK signature verifier, and a small manifest audit tool. Inputs and decompiled material stay in ignored `.local/`; proprietary APKs, firmware, credentials and decompiled app sources are not redistributed.

Run the tooling tests with Python 3.10 or newer:

```sh
python -m unittest discover -s tests -v
```

See [reproduce.md](docs/reproduce.md) for inspecting the exact APK versions. These are desktop research tools, not requirements for an eventual rider-facing app.

## Existing work

[better-dash](https://github.com/norbertFeron/better-dash), [OpenDash](https://github.com/subtlesayak/open-dash), and [Open Headunit](https://github.com/andreknieriem/open-headunit) already solve important parts of the problem. [REA](https://github.com/morluto/rea) supplied a useful toolchain reference and a pinned JADX engine. Their respective licenses apply to their code; this repository's original tooling is MIT-licensed.

Independent community research. Not affiliated with Royal Enfield, Google, or Apple. Android Auto and CarPlay are separate projection systems; an iPhone screen-off navigation app is not evidence of CarPlay support.

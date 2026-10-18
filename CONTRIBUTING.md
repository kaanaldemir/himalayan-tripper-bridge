# Contributing

The first objective is to settle full Android Auto startup on the same phone under the constraints in [findings.md](docs/findings.md). A custom map renderer is useful elsewhere, but is not a substitute for that objective here.

For a finding, include the exact Android Auto/app version and file hash, the relevant component or class/method, whether the evidence is static or runtime, and any unresolved prerequisites. Label an inference or proposed experiment as such. Do not call a parsed link, accepted socket, or simulated peer a working Android Auto session.

Do not upload APKs, firmware images, credentials, private certificates or keys, decompiled source archives, personal route history, or raw account data. `.local/` is ignored for analysis inputs and outputs. Minimal original descriptions and reproducible commands are preferred.

Before adding receiver code from another project, establish and retain its license obligations. Do not apply this repository's MIT license to code imported under a different license.

Run `python -m unittest discover -s tests -v` for changes to the manifest tool. Java helpers compile against the exact pinned JARs in `tools/prepare-tools.ps1`. Update findings only to the extent supported by the validation performed.

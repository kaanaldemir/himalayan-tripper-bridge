# Executable reconstruction and virtual validation

The desktop probes exercise specific reconstructed mechanisms. They do not run Android Auto or the Royal Enfield APK. No APK-derived private key, firmware, decompiled code dump or device credential is distributed.

| Executed check | What it establishes | What it does not establish |
| --- | --- | --- |
| Python unit suite (16 tests) | K1G byte fixtures, parser truncation rejection, supported ACKs, RTP FU-A framing/wrap and model bookkeeping | Actual dash compatibility or phone behavior |
| `tools/virtual_link.py` | Real loopback UDP transfer, byte reassembly, sequence wrap and two synthetic decoder ACK exchanges | Authentication, H.264 decoding, an AA frame or a physical dash |
| `tools/DashAuthProbe.java` | SSID + 32 random session bytes round-trip under an independently generated RSA-1024 key, 128 ciphertext bytes | Dash key exchange, session sequencing or actual authentication |
| `tools/ReceiverCertificateProbe.java` | Pinned upstream public receiver certificate validates against the public automotive CA under the JDK trust provider | Android runtime, private-key possession, WPP or AAP |
| `tools/ReceiverTlsProbe.java` | Actual loopback TLS 1.2 with reversed TCP/TLS roles, required client authentication, supplied upstream receiver credentials and synthetic echo bytes | Real phone startup, WPP message handling or a full AA session |
| `bootstrap_model.py` | A reviewable representation of identified caller, feature and presence guards | Execution of those guards inside Android or discovery of unknown paths |

## Dash wire probe

```sh
python -m unittest discover -s tests -v
python tools/virtual_link.py
java tools/DashAuthProbe.java
```

The wire run transferred 6,145 synthetic bytes in five RTP datagrams, at most 1,372 bytes each. It reassembled SHA-256 `7b4c3fdbab6f736e52db8f8dba82cfad781e7c75f76261ad591e318a1a864ff2` and completed two ACK exchanges. The sample NAL payload is **not decodable video**.

`bridgewire.py` includes the observed phone control header and short incoming dash-event format, strict TLV parsing, decoded-frame/button ACKs, and a single-NAL/FU-A packetizer. The following are still absent: complete authenticated session state, key-fragment assembly, discovery/reconnect policy, heartbeat scheduling, codec configuration, video capture/rendering, encryption for secure telemetry, and AAP.

## Certificate and TLS probes

Use independently obtained **public** automotive CA and receiver certificate files. The original run used the CA exposed by the inspected `sae` trust setup and the pinned Open Headunit `app/src/main/res/raw/cert` file. See [certificate fingerprints](android-auto-bootstrap.md). Keep all inputs in ignored `.local/`.

```sh
java tools/ReceiverCertificateProbe.java .local/automotive-ca.pem .local/receiver-cert.pem
```

For the loopback probe, a supplied receiver PKCS#8 key must match its certificate. The original run used Open Headunit's openly supplied receiver material without copying it into this repository. No APK key was decrypted or used. Generate a **disposable synthetic server** identity locally with your JDK:

```sh
keytool -genkeypair -alias synthetic-server -keyalg RSA -keysize 2048 -dname "CN=Synthetic Loopback Only" -validity 1 -storetype PKCS12 -keystore .local/synthetic-server.p12 -storepass disposable-test-only -noprompt
java tools/ReceiverTlsProbe.java .local/automotive-ca.pem .local/receiver-cert.pem .local/receiver-pkcs8.pem .local/synthetic-server.p12
```

The keystore password above is only for this disposable fixture; the probe accepts `SYNTHETIC_TLS_STORE_PASSWORD` if changed. It binds only 127.0.0.1 on an ephemeral port, uses five-second socket timeouts, and authenticates the receiver against the supplied CA. The receiver side trusts only the synthetic server certificate. It does not use a trust-all manager. Private fixture material stays local and is not a deliverable.

The original run passed both checks. A synthetic server can reproduce TLS roles and the observed client-trust rule. It cannot reproduce Google's server-side configuration, Android's Binder caller identity, Android network selection, sender process lifecycle, or the full projection implementation.

## Why reconstructing more source is not equivalent to running the product

Decompiled Java helps explain control flow; smali checks critical branches. Neither recovers lost comments, original names, build infrastructure or server-held state. A source-derived model tests our reconstruction, and cannot certify it independently. The probes above therefore separate protocol facts we executed from the phone-side decisions we only inspected.

A full hardware-free phone-side demonstration would require the stock sender to run in an Android environment, enter a permitted startup route and finish WPP/AAP with the receiver. Firmware reverse engineering alone cannot supply that sender authorization. A bike is unnecessary for investigating this specific dependency, but substituting a Python model for the sender would not resolve it.

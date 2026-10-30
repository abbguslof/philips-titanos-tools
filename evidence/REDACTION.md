# Redaction policy

The private research archive contains raw logs, packet captures, firmware, and
full partition dumps. The public tree contains only the minimum evidence needed
to support a claim.

## Removed or replaced

| Data | Action |
| :--- | :--- |
| TV serial number | Removed; examples use `SERIAL` or a placeholder. |
| MAC addresses / BSSID | Replaced with `02:00:00:00:00:00` or removed. |
| Wi-Fi SSID | Removed; examples use `ExampleWiFi`. |
| Pairing PIN / credentials | Removed; `.jointspace_credentials.json` is never copied. |
| Private/home IP addresses | Replaced with `192.0.2.0/24` documentation addresses. |
| Workstation username/path | Removed; docs use repo-relative paths. |
| Vendor application secret | Removed from code and docs; supplied via environment. |
| Raw packet captures | Not published; aggregate findings only. |
| 3 MB system logs | Not published; selected redacted excerpts only. |
| Full 4 MB partition dumps | Replaced with 32-byte `UMFG` slices and hashes. |
| Firmware packages / extracted rootfs | Not published; acquisition and extraction are documented. |
| Private keys / generated certs | Not published; regenerate locally. |

## Placeholder conventions

- TV address: `192.0.2.10`
- Workstation address: `192.0.2.44`
- Generic device: `192.0.2.0/24`
- MAC: `02:00:00:00:00:00`
- Serial: `SERIAL` or `FZA1A0000000000`
- PIN: `0000`

## Before adding evidence

1. Prove the claim with the smallest possible file.
2. Run `grep -R` for the patterns above.
3. Check that the file does not contain a real serial, MAC, SSID, IP, or token.
4. Prefer a hash or a 32-byte slice over a full dump.
5. Update [README.md](README.md) and note the redaction.

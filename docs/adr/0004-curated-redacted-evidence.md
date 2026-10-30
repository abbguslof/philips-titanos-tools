# Publish curated, redacted evidence

Raw logs and packet captures contain the TV serial, MAC addresses, SSID/BSSID, pairing PIN, private IPs, and workstation paths. We will publish short, redacted excerpts and hashes that prove the claim, not the raw captures.

**Status:** accepted

**Consequences:** A reader cannot replay every packet, but can verify the important transitions (root, listener, UMFG slices, failure modes). The public evidence stays small and safe; the private archive keeps the raw data.

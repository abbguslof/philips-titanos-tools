# Publish a clean, sanitized tree from a fresh history

The research repository's public history contains a bridge password and a vendor application secret, plus raw device logs. We will publish a fresh, sanitized tree instead of force-pushing a rewritten history. The old repository stays private as a research archive, and the exposed credentials must be rotated independently.

**Status:** accepted

**Consequences:** The public repository has no secret-bearing history. Contributors should not assume the old commit IDs exist. The private archive keeps the raw evidence.

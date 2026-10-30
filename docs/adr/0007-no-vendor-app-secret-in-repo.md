# Do not ship the vendor JointSpace application secret

The research history contained a base64 application secret used by the official Philips client for JointSpace pairing. It is a vendor secret, not project code. We removed it from the public tree and made the client read `PHILIPS_APP_SECRET` or `PHILIPS_APP_SECRET_FILE`.

**Status:** accepted

**Consequences:** Pairing is not zero-config; a user must supply the secret from their own research. The root path does not need it. This avoids republishing a vendor credential in a new public history.

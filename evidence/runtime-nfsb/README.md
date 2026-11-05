# Runtime NFSB bypass evidence

Redacted live captures from 2026-11-05. The target is the documented
`55PUS8000/12`. IP addresses, serials, MACs, and credentials are removed.

| File | What it shows |
| :--- | :--- |
| [mount-nfsb.txt](mount-nfsb.txt) | A pristine NFSB mount verifies the header and creates linear and verity targets. |
| [modified-nfsb.txt](modified-nfsb.txt) | A modified NFSB copy still mounts, but dm-verity rejects the changed block on read. |
| [raw-squashfs.txt](raw-squashfs.txt) | A direct `squashfs` mount of the inner filesystem at offset `0x1000` succeeds without the NFSB verifier. |

The method and limits are in
[runtime NFSB bypass](../../docs/research/17-runtime-nfsb-squashfs.md).

# Keep the autorun and SAM USB workflows separate

The boot autorun hook only finds `/media/sda1`, and mdev mounts an unlabelled partition there; a labelled partition lands elsewhere. The SAM `Download from USB` path expects a volume labelled `PHILIPS`. We will document and tool these as two different sticks rather than trying to make one stick satisfy both.

**Status:** accepted

**Consequences:** The autoroot builder enforces an empty FAT32 label. The SAM prep tool keeps the `PHILIPS` label. A user must reformat when switching workflows.

# Excluded v1 partial attempt

This directory preserves the first scheduled `2026-07-11-v1` attempt and its schedule after a
runner finalization defect was discovered. The process reached inference, but it did not produce an
eligible finalized attempt. It contributes neither prediction-quality nor process evidence to v2.

Before v2 was frozen, only operating-system process state and the trace file's byte size were
inspected. The event contents, prediction contents, and workspace contents were not inspected. The
regular files were copied without modification and verified against
`results/excluded/v1-finalizer-bug.sha256`. The payload is retained locally and on the VPS but ignored
by Git; the checksum ledger, schedule, and this exclusion note are the public records.

- Regular files in the pre-copy manifest: `112`
- SHA-256 of that manifest: `05942aa5bebd7f45787cb6e5e57f54909f69bc60cd96e8c56be12cae0794eaf2`
- Exclusion reason: the v1 finalizer referenced unbound variables before classification under
  `set -u`
- v2 policy: restart every registered cell from replicate 1 after a new public freeze tag

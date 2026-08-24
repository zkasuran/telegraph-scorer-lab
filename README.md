# telegraph-scorer-lab (private)

Private working repo for the Telegraph salience scorer. This is where the method
lives: the scoring module source, the research and tuning sweeps, the build and
registration drivers, and the worklogs.

The public repo `zkasuran/telegraph-salience-scorer` is a host and verification
surface only: it serves the champion `dist/*.wasm` binaries the node fetches at
commit-pinned raw URLs, plus the harness and fixtures a judge needs to verify a
score. It must stay public while any live registration points at it.

Do method work here, not there.

## Layout

```
module/src/        scoring module source (Rust, no_std)
research/          exploration: agreement/spearman sweeps, score dumps, variant diffs
scorer-drivers/    build + gate + register automation (deploy/reclaim/variants/tune)
harness/           Go + wazero harness (verification)
bench/             fixtures, attack suite, family benchmarks
worklogs/          LEDGER, HANDOFF, SUBMIT-PACKET
```

## Build / gate / register

Drivers assume a checkout of the public host repo alongside this one (they commit
built binaries to its `dist/` and register the raw URL on-chain). See
`scorer-drivers/deploy.py` and `scorer-drivers/reclaim.py`.

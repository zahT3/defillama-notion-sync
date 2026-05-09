# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-05-09

### Added
- Initial release.
- Fetch per-chain TVL from `https://api.llama.fi/v2/chains`.
- Fetch per-chain 24h fee revenue from `https://api.llama.fi/overview/fees/chains`.
- Sync `24h 收入 (USD)` / `TVL (USD)` / `最近动态日` to a Notion database
  via the Notion API, keyed off a configurable `COMPANY_TO_CHAIN` mapping.
- `--dry-run` to preview changes without writing.
- `--verbose` for debug-level logging.
- GitHub Actions workflow (`.github/workflows/weekly-sync.yml`) that runs
  every Monday at 09:00 UTC and supports manual `workflow_dispatch`.
- MIT license.

### Known limitations
- Chain-only matching (no protocol-level revenue yet — coming in 0.2.0).
- `COMPANY_TO_CHAIN` is hard-coded; multi-source / fuzzy matching is a
  future enhancement.

# defillama-notion-sync

> Filter Web3 job-target companies by **real on-chain revenue**, not Twitter
> hype. It piped DeFiLlama's chain economics into a Notion shortlist used to
> decide where to apply.
>
> **Archived 2026-09-17** — the shortlist it fed is no longer active, so the
> weekly cron was removed and this repository was archived. The code stays
> here as a reference; run it by hand from the Actions tab if you revive it.

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

## The problem

Web3 job boards list 5,000+ openings on any given day. After the 2024
post-token-launch shakeout, an uncomfortable number of those companies are
**token-rich and revenue-poor** — the kind that look great on Twitter,
sponsor a hackathon, and quietly lay off engineering six months later.
Picking targets by "is this protocol on Twitter trending" is a great way
to invest a month preparing for an interview at a company that won't
exist when you'd start.

**Daily protocol revenue** is one of the few signals you can't fake. If
chain X is generating real fees, real users are paying it. That money has
to land somewhere — and one place it lands is the engineering payroll.

## The system

I keep a Notion database of Web3 companies I'd consider applying to. Each
row has stuff Notion is good at (career page URL, my interest level,
remote policy, Chinese-friendliness, application status, link to job
listings I've tracked). What Notion is *not* good at is keeping the
"is this company actually printing money" column up to date.

This script is the answer:

```
DeFiLlama API → match by chain name → Notion company shortlist
                                          ↓
                            "24h Revenue (USD)"  +  "TVL (USD)"  +  "Last Updated"
```

While the cron was running it refreshed the numbers every Monday at 9am, so
planning the week's applications started from a fresh signal.

## What it actually does

1. `GET https://api.llama.fi/v2/chains` → per-chain TVL
2. `GET https://api.llama.fi/overview/fees/chains` → per-chain 24h fee revenue
3. Pull all rows from the Notion database
4. For each row whose `公司` (Company) maps to a chain in `COMPANY_TO_CHAIN`,
   diff against current values and `PATCH` the page if anything changed
5. Log a one-line summary per company; only network-write what's actually different

It's ~150 lines of straightforward Python: `requests` for DeFiLlama,
`notion-client` for Notion, `python-dotenv` for secrets. No frameworks,
no clever abstractions.

## Quickstart

```bash
git clone https://github.com/zahT3/defillama-notion-sync.git
cd defillama-notion-sync
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in NOTION_TOKEN + NOTION_DATABASE_ID
python sync.py --dry-run --verbose
```

Create a Notion integration at <https://www.notion.so/my-integrations>,
then **share** the target database with that integration (database `…`
menu → Connections → add the integration). The integration token goes
into `.env`.

## Run modes

```bash
python sync.py                # do the update
python sync.py --dry-run      # preview only — does not write to Notion
python sync.py --verbose      # debug logging
```

Sample output:

```
2026-05-09 09:00:01 [llama] INFO Fetching TVL from https://api.llama.fi/v2/chains
2026-05-09 09:00:02 [llama] INFO Fetching 24h revenue from https://api.llama.fi/overview/fees/chains
2026-05-09 09:00:02 [sync]  INFO Loaded stats for 312 chains from DeFiLlama
2026-05-09 09:00:03 [sync]  INFO Loaded 23 company rows from Notion
2026-05-09 09:00:03 [sync]  INFO UPD | Solana Foundation / Solana Labs | rev: $3.43M -> $3.51M | tvl: $9.20B -> $9.34B
2026-05-09 09:00:03 [sync]  INFO UPD | Hyperliquid Labs              | rev: $2.97M -> $3.12M | tvl: —      -> —
2026-05-09 09:00:04 [sync]  INFO Done. updates=8 skipped=15 total=23
```

## Scheduling

### GitHub Actions (recommended — zero-infra)

A workflow is included at `.github/workflows/weekly-sync.yml`. Its cron was
removed when this repository was archived, so it now runs only on manual
dispatch. To use it:

1. Push this repo to GitHub.
2. Repo → Settings → Secrets and variables → Actions → add:
   - `NOTION_TOKEN`
   - `NOTION_DATABASE_ID`
3. Optionally trigger it manually once: Actions tab → "weekly-sync" →
   "Run workflow" to verify it works.

### Local cron (if you prefer)

```cron
0 9 * * 1  cd /path/to/defillama-notion-sync && /path/to/.venv/bin/python sync.py >> sync.log 2>&1
```

## Extending

### Add a new chain mapping

Edit `COMPANY_TO_CHAIN` in `sync.py`:

```python
COMPANY_TO_CHAIN = {
    "Avalanche Labs": "Avalanche",  # Notion company title -> DeFiLlama chain name
    ...
}
```

### Pull additional metrics

DeFiLlama exposes a lot more than TVL and fees:
[active addresses, stablecoin volume, DEX volume, perps volume, bridge
volume](https://github.com/DefiLlama/DefiLlama-Adapters). Each is a
separate endpoint — add a fetcher and an extra `properties` field on
the Notion update.

### Match by protocol instead of chain

`/overview/fees` returns per-protocol rows too (Uniswap, Aave, Hyperliquid
DEX, etc.). For app-layer companies (vs. L1s), the protocol-level
revenue is more relevant. The existing chain-only matching is a
deliberate v1 simplification.

## Why I built this

This is one piece of a larger job-hunt system I'm running while
transitioning from fintech ops to Web3 + AI Agent engineering. The other
pieces — JD-keyword mapping, cover-letter templates, application tracker
relations — live in Notion. This script is the only part that benefits
from being open-source: anyone running a similar Notion shortlist can
fork it.

It's also a deliberate portfolio artifact:

- **Domain literacy**: I know which DeFiLlama endpoints to use and why
  daily fee revenue is the meaningful filter.
- **Python + API hygiene**: pagination, idempotent updates, dry-run,
  structured logging, env-based config.
- **Workflow-as-code**: the GitHub Actions workflow is the same pattern
  I use for AI Agent automation in my day job.
- **Pragmatism**: I'm not over-engineering. There's no ORM, no async, no
  abstract base class. The script does one thing.

## License

MIT

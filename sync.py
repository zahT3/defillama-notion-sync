"""
DeFiLlama → Notion sync for the 「🎯 目标公司狩猎名单」 database.

Fetches 24h revenue + TVL from DeFiLlama and updates the matching
company rows in Notion. Designed to run weekly via cron / GitHub Actions.

Usage:
    python sync.py                # update Notion in place
    python sync.py --dry-run      # preview changes only
    python sync.py --verbose      # show debug output
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import os
import sys
from dataclasses import dataclass
from typing import Any

import requests
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

LLAMA_CHAINS_URL = "https://api.llama.fi/v2/chains"
LLAMA_FEES_URL = (
    "https://api.llama.fi/overview/fees/chains"
    "?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true"
)

# Map "公司" title in Notion -> DeFiLlama chain name (or None if not on-chain)
# Add aliases here when name mismatches.
COMPANY_TO_CHAIN = {
    "Solana Foundation / Solana Labs": "Solana",
    "Hyperliquid Labs": "Hyperliquid L1",
    "Mysten Labs (Sui)": "Sui",
    "Aptos Labs": "Aptos",
    "Tron": "Tron",
    "Polygon Labs": "Polygon",
    "Sei Labs": "Sei",
    "Coinbase / Coinbase Developer Platform": "Base",  # Base = Coinbase L2
    # add as you go: "Avalanche Labs": "Avalanche", etc.
}


@dataclass
class ChainStats:
    name: str
    revenue_24h: float | None
    tvl: float | None


def fetch_chain_stats() -> dict[str, ChainStats]:
    """Fetch DeFiLlama chain TVL + 24h revenue, keyed by chain name."""
    log = logging.getLogger("llama")

    log.info("Fetching TVL from %s", LLAMA_CHAINS_URL)
    chains_resp = requests.get(LLAMA_CHAINS_URL, timeout=30)
    chains_resp.raise_for_status()
    tvl_by_name = {row["name"]: row.get("tvl") for row in chains_resp.json()}

    log.info("Fetching 24h revenue from %s", LLAMA_FEES_URL)
    fees_resp = requests.get(LLAMA_FEES_URL, timeout=30)
    fees_resp.raise_for_status()
    fees_payload = fees_resp.json().get("protocols", [])
    revenue_by_name = {row["name"]: row.get("total24h") for row in fees_payload}

    all_names = set(tvl_by_name) | set(revenue_by_name)
    return {
        name: ChainStats(
            name=name,
            revenue_24h=revenue_by_name.get(name),
            tvl=tvl_by_name.get(name),
        )
        for name in all_names
    }


def get_company_title(page: dict[str, Any]) -> str:
    title = page["properties"].get("公司", {}).get("title", [])
    return "".join(part.get("plain_text", "") for part in title)


def get_current_revenue(page: dict[str, Any]) -> float | None:
    return page["properties"].get("24h 收入 (USD)", {}).get("number")


def get_current_tvl(page: dict[str, Any]) -> float | None:
    return page["properties"].get("TVL (USD)", {}).get("number")


def update_page(notion: Client, page_id: str, revenue: float | None, tvl: float | None) -> None:
    today = dt.date.today().isoformat()
    properties: dict[str, Any] = {
        "最近动态日": {"date": {"start": today}},
    }
    if revenue is not None:
        properties["24h 收入 (USD)"] = {"number": float(revenue)}
    if tvl is not None:
        properties["TVL (USD)"] = {"number": float(tvl)}
    notion.pages.update(page_id=page_id, properties=properties)


def sync(dry_run: bool = False) -> None:
    log = logging.getLogger("sync")

    if not NOTION_TOKEN or not DATABASE_ID:
        log.error("Missing NOTION_TOKEN or NOTION_DATABASE_ID. See .env.example.")
        sys.exit(1)

    chain_stats = fetch_chain_stats()
    log.info("Loaded stats for %d chains from DeFiLlama", len(chain_stats))

    notion = Client(auth=NOTION_TOKEN)
    pages = []
    cursor = None
    while True:
        kwargs: dict[str, Any] = {"database_id": DATABASE_ID, "page_size": 100}
        if cursor:
            kwargs["start_cursor"] = cursor
        resp = notion.databases.query(**kwargs)
        pages.extend(resp.get("results", []))
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")
    log.info("Loaded %d company rows from Notion", len(pages))

    updates = 0
    skipped = 0
    for page in pages:
        company = get_company_title(page).strip()
        chain_key = COMPANY_TO_CHAIN.get(company)
        if not chain_key:
            log.debug("skip (no chain mapping): %s", company)
            skipped += 1
            continue

        stats = chain_stats.get(chain_key)
        if stats is None:
            log.warning("DeFiLlama has no row for %s -> %s", company, chain_key)
            skipped += 1
            continue

        prev_rev = get_current_revenue(page)
        prev_tvl = get_current_tvl(page)
        revenue_changed = stats.revenue_24h is not None and stats.revenue_24h != prev_rev
        tvl_changed = stats.tvl is not None and stats.tvl != prev_tvl

        if not (revenue_changed or tvl_changed):
            log.debug("no change: %s", company)
            continue

        log.info(
            "%s | %s | rev: %s -> %s | tvl: %s -> %s",
            "DRY" if dry_run else "UPD",
            company,
            _fmt(prev_rev),
            _fmt(stats.revenue_24h),
            _fmt(prev_tvl),
            _fmt(stats.tvl),
        )

        if not dry_run:
            update_page(notion, page["id"], stats.revenue_24h, stats.tvl)
        updates += 1

    log.info("Done. updates=%d skipped=%d total=%d", updates, skipped, len(pages))


def _fmt(value: float | None) -> str:
    if value is None:
        return "—"
    if value >= 1e9:
        return f"${value / 1e9:.2f}B"
    if value >= 1e6:
        return f"${value / 1e6:.2f}M"
    if value >= 1e3:
        return f"${value / 1e3:.1f}K"
    return f"${value:.0f}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Preview changes only")
    parser.add_argument("--verbose", "-v", action="store_true", help="Debug logs")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    )
    sync(dry_run=args.dry_run)


if __name__ == "__main__":
    main()

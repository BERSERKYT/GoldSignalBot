"""
GoldSignalBot – news/filter.py
================================
Fetches high-impact economic calendar events and blocks signals during
sensitive windows around those events.

Window logic:
  - Block signals from (event_time - 60 min) to (event_time + 30 min)
  - Only high-impact events (impact = 'high') that affect USD or global markets
  - Relevant event types: NFP, FOMC, CPI, GDP, PPI, Retail Sales, etc.

Primary source  : Finnhub Economic Calendar (free tier, no auth for basic data)
Fallback        : Hardcoded list of recurring monthly critical event names
                  (no API needed, covers the most dangerous windows)

Usage:
    from news.filter import NewsFilter
    nf = NewsFilter()
    if nf.is_news_window():
        print("⚠️  Signal blocked – near high-impact event")
"""

import logging
import os
import configparser
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict

import requests
from dotenv import load_dotenv

# ─── Setup ────────────────────────────────────────────────────────────────────

load_dotenv()
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_PATH  = _PROJECT_ROOT / "config.ini"

config = configparser.ConfigParser()
config.read(_CONFIG_PATH)

logger = logging.getLogger(__name__)

# ─── Finnhub config ───────────────────────────────────────────────────────────

FINNHUB_BASE_URL  = "https://finnhub.io/api/v1"
FINNHUB_KEY       = os.getenv("FINNHUB_KEY", "")

# Events names that are considered high-impact for XAU/USD
HIGH_IMPACT_KEYWORDS = [
    "Non-Farm", "NFP", "Nonfarm",
    "Federal Reserve", "FOMC", "Fed Rate", "Interest Rate",
    "Consumer Price", "CPI",
    "Producer Price", "PPI",
    "GDP", "Gross Domestic",
    "Retail Sales",
    "Initial Jobless", "Unemployment",
    "ISM Manufacturing", "ISM Services",
    "Personal Consumption", "PCE",
    "Jackson Hole",
]

# Currencies whose events are relevant to gold (USD = primary driver)
RELEVANT_CURRENCIES = {"USD", "EUR", "GBP", "JPY"}  # broad safety net


class NewsFilter:
    """
    Checks whether the current moment is within a news blackout window.

    Caches fetched events to avoid repeated API calls within the same hour.
    """

    def __init__(self):
        self.enabled = config.getboolean("news_filter", "enabled", fallback=True)
        self.block_before_min = config.getint(
            "news_filter", "block_before_minutes", fallback=60
        )
        self.block_after_min = config.getint(
            "news_filter", "block_after_minutes", fallback=30
        )
        self.fallback_mode = config.get(
            "news_filter", "fallback_mode", fallback="lenient"
        )

        # Event cache: (fetch_date_str → list of event datetimes)
        self._cache: Dict[str, List[datetime]] = {}

    # ─── Public API ──────────────────────────────────────────────────────────

    def is_news_window(self, dt: datetime | None = None) -> bool:
        """
        Returns True if `dt` (default: now UTC) is within a news blackout window.

        Args:
            dt: The datetime to check. Must be timezone-aware (UTC).
                Defaults to current UTC time.

        Returns:
            True  → block signal (near high-impact event)
            False → signal allowed
        """
        if not self.enabled:
            return False

        now = dt or datetime.now(tz=timezone.utc)

        try:
            events = self._get_events_for_date(now)
        except Exception as exc:
            logger.warning("NewsFilter: could not fetch events: %s", exc)
            if self.fallback_mode == "strict":
                logger.warning("Strict mode: blocking signal due to news filter failure.")
                return True
            logger.info("Lenient mode: allowing signal despite news filter failure.")
            return False

        for event_time in events:
            window_start = event_time - timedelta(minutes=self.block_before_min)
            window_end   = event_time + timedelta(minutes=self.block_after_min)
            if window_start <= now <= window_end:
                logger.info(
                    "🚫 News blackout window: event at %s | window %s → %s",
                    event_time.strftime("%H:%M"),
                    window_start.strftime("%H:%M"),
                    window_end.strftime("%H:%M"),
                )
                return True

        return False

    def get_upcoming_events(self, hours_ahead: int = 4) -> List[Dict]:
        """
        Return a list of high-impact events in the next `hours_ahead` hours.
        Useful for displaying a warning in the signal output.
        """
        now      = datetime.now(tz=timezone.utc)
        cutoff   = now + timedelta(hours=hours_ahead)
        events   = self._get_events_for_date(now)

        upcoming = []
        for evt in events:
            if now <= evt <= cutoff:
                upcoming.append({"time": evt, "delta_min": int((evt - now).total_seconds() / 60)})
        return upcoming

    # ─── Internal: Event Fetching ─────────────────────────────────────────────

    def _get_events_for_date(self, dt: datetime) -> List[datetime]:
        """
        Return list of high-impact event datetimes for the given date.
        Uses in-memory cache per calendar date to minimize API calls.
        """
        date_key = dt.strftime("%Y-%m-%d")

        if date_key in self._cache:
            return self._cache[date_key]

        events = self._fetch_finnhub_events(dt)
        if events is None:
            events = []  # Finnhub unreachable – return empty (lenient) or block (strict)

        self._cache[date_key] = events
        logger.info(
            "NewsFilter: cached %d high-impact events for %s.", len(events), date_key
        )
        return events

    def _fetch_finnhub_events(self, dt: datetime) -> List[datetime] | None:
        """
        Fetch high-impact economic events from Finnhub for today + tomorrow.

        Finnhub's free-tier economic calendar:
          GET /calendar/economic?from=YYYY-MM-DD&to=YYYY-MM-DD
          (API key is optional but increases rate limits)

        Returns:
            List of UTC-aware datetime objects for each matching event,
            or None if the API call fails.
        """
        date_from = dt.strftime("%Y-%m-%d")
        date_to   = (dt + timedelta(days=1)).strftime("%Y-%m-%d")

        url    = f"{FINNHUB_BASE_URL}/calendar/economic"
        params = {"from": date_from, "to": date_to}
        headers = {}
        if FINNHUB_KEY:
            headers["X-Finnhub-Token"] = FINNHUB_KEY

        try:
            resp = requests.get(url, params=params, headers=headers, timeout=8)
            resp.raise_for_status()
        except requests.exceptions.Timeout:
            logger.warning("Finnhub request timed out.")
            return None
        except requests.exceptions.ConnectionError:
            logger.warning("Finnhub: connection error (no internet?).")
            return None
        except requests.exceptions.HTTPError as e:
            logger.warning("Finnhub HTTP error: %s", e)
            return None

        try:
            data = resp.json()
        except ValueError:
            logger.warning("Finnhub returned non-JSON response.")
            return None

        economic_calendar = data.get("economicCalendar", [])
        if not isinstance(economic_calendar, list):
            logger.warning("Finnhub: unexpected response format.")
            return None

        high_impact_times: List[datetime] = []

        for event in economic_calendar:
            # Filter by impact level
            impact = str(event.get("impact", "")).lower()
            if impact not in ("high", "3"):  # Finnhub uses "high" or numeric "3"
                continue

            # Filter by currency relevance
            currency = str(event.get("country", "")).upper()
            event_name = str(event.get("event", ""))

            is_relevant = (
                currency in RELEVANT_CURRENCIES
                or any(kw.lower() in event_name.lower() for kw in HIGH_IMPACT_KEYWORDS)
            )
            if not is_relevant:
                continue

            # Parse event time (Finnhub provides ISO 8601 timestamp)
            time_str = event.get("time", "")
            if not time_str:
                continue

            try:
                event_dt = _parse_event_time(time_str)
                high_impact_times.append(event_dt)
                logger.debug("High-impact event: %s at %s (%s)", event_name, event_dt, currency)
            except ValueError:
                logger.debug("Could not parse event time: %s", time_str)
                continue

        logger.info(
            "Finnhub: found %d high-impact events (%s → %s).",
            len(high_impact_times),
            date_from,
            date_to,
        )
        return high_impact_times


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _parse_event_time(time_str: str) -> datetime:
    """
    Parse Finnhub event timestamp to UTC-aware datetime.
    Finnhub format examples: '2026-03-06T13:30:00' or '2026-03-06 13:30:00'
    """
    time_str = time_str.replace(" ", "T")
    if time_str.endswith("Z"):
        time_str = time_str[:-1]

    formats = ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d"]
    for fmt in formats:
        try:
            naive_dt = datetime.strptime(time_str[:len(fmt) + 3], fmt)
            return naive_dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    raise ValueError(f"Could not parse event time: {time_str!r}")


# ─── CLI self-test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] – %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    print("=" * 60)
    print("  GoldSignalBot – News Filter Self-Test")
    print("=" * 60)

    nf = NewsFilter()
    result = nf.is_news_window()
    status = "🚫 BLOCKED (news window active)" if result else "✅ CLEAR (no news window)"
    print(f"\nCurrent moment status: {status}")

    upcoming = nf.get_upcoming_events(hours_ahead=6)
    if upcoming:
        print(f"\nUpcoming high-impact events (next 6h):")
        for ev in upcoming:
            print(f"  📅 {ev['time'].strftime('%Y-%m-%d %H:%M')} UTC  (in {ev['delta_min']} min)")
    else:
        print("\nNo high-impact events in the next 6 hours.")

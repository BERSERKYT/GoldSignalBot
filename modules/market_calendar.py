import logging
from datetime import datetime, time, timezone

logger = logging.getLogger("MarketCalendar")

def is_market_open() -> bool:
    """
    Checks if the Gold (XAU/USD) market is currently open.
    Gold Spot typically opens on Sunday at 23:00 UTC and closes on Friday at 21:00 UTC.
    """
    now_utc = datetime.now(timezone.utc)
    weekday = now_utc.weekday()  # Monday is 0, Sunday is 6
    hour = now_utc.hour
    
    # 1. Closed on Saturday (5)
    if weekday == 5:
        logger.info("🚫 Market Status: CLOSED (Saturday)")
        return False
        
    # 2. Friday: Closes at 21:00 UTC
    if weekday == 4:
        if hour >= 21:
            logger.info(f"🚫 Market Status: CLOSED (Friday after 21:00 UTC, current: {hour}:00)")
            return False
            
    # 3. Sunday: Opens at 23:00 UTC
    if weekday == 6:
        if hour < 22: # Conservative open at 22:00 UTC
            logger.info(f"🚫 Market Status: CLOSED (Sunday before 22:00 UTC, current: {hour}:00)")
            return False
            
    logger.info(f"✅ Market Status: OPEN ({now_utc.strftime('%A %H:%M UTC')})")
    return True

if __name__ == "__main__":
    # Test script
    logging.basicConfig(level=logging.INFO)
    print(f"Is market open now? {is_market_open()}")

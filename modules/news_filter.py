import os
import requests
import datetime
from datetime import timedelta, timezone
import logging

logger = logging.getLogger(__name__)

class NewsFilter:
    """
    Checks Finnhub's Economic Calendar for high-impact USD events.
    If an event is within ±60 minutes (or as configured) of the signal generation time,
    it returns False indicating it is NOT safe to trade.
    """
    def __init__(self):
        self.api_key = os.getenv("FINNHUB_KEY")
        self.pre_event_buffer_mins = 60
        self.post_event_buffer_mins = 30
        
    def is_safe_to_trade(self, current_time: datetime.datetime = None) -> bool:
        """
        Returns True if it is safe to trade (no high-impact news within buffer).
        Returns False if a high-impact USD news event is too close.
        """
        if not self.api_key:
            logger.warning("No FINNHUB_KEY found. News filter disabled. Proceeding with caution.")
            return True # If no API key, bypass the filter so bot can still run
            
        if current_time is None:
            current_time = datetime.datetime.now(timezone.utc)
            
        # Ensure current_time is UTC aware
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)
            
        # Fetch today's economic calendar from Finnhub
        # Format: from / to (YYYY-MM-DD)
        today_str = current_time.strftime('%Y-%m-%d')
        tomorrow_str = (current_time + timedelta(days=1)).strftime('%Y-%m-%d')
        
        url = f"https://finnhub.io/api/v1/calendar/economic?from={today_str}&to={tomorrow_str}&token={self.api_key}"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            events = data.get('economicCalendar', [])
            
            for event in events:
                # Filter for High impact USD news (often denoted as impact='High' or similar, varies by provider)
                # Finnhub provides "impact" (e.g., "high", "medium", "low", "OPEC") or missing sometimes.
                # Assuming 'country' == 'US' and 'impact' == 'high' (will need safe lower() checks)
                
                country = event.get('country', '').upper()
                impact = event.get('impact', '').lower()
                
                # Gold is heavily influenced by US news, sometimes EU/CN but V1 specification said "high-impact USD/global events"
                if country in ['US'] and impact == 'high':
                    event_time_str = event.get('time')
                    if event_time_str:
                        # Finnhub time string: "2024-03-01 13:30:00" in UTC usually
                        event_time = datetime.datetime.strptime(event_time_str, "%Y-%m-%d %H:%M:%S")
                        event_time = event_time.replace(tzinfo=timezone.utc)
                        
                        # Calculate buffers
                        danger_start = event_time - timedelta(minutes=self.pre_event_buffer_mins)
                        danger_end = event_time + timedelta(minutes=self.post_event_buffer_mins)
                        
                        if danger_start <= current_time <= danger_end:
                            event_name = event.get('event', 'Unknown Event')
                            logger.warning(f"NEWS FILTER TRIGGERED: High impact US event '{event_name}' at {event_time_str} UTC.")
                            return False # NOT safe to trade
                            
            logger.debug("News check passed. Safe to trade.")
            return True
            
        except Exception as e:
            logger.error(f"Error fetching calendar from Finnhub: {e}. Defaulting to safe=True to avoid locking up.")
            return True

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    nfilter = NewsFilter()
    safe = nfilter.is_safe_to_trade()
    print(f"Safe to trade right now? {safe}")

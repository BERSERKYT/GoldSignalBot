import os
import requests
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

logger = logging.getLogger("SentimentEngine")

class SentimentEngine:
    """
    Analyzes global market news to determine a Bullish/Bearish bias for Gold (XAU/USD).
    Higher score (> 0.2) = Bullish (Safe-haven demand, weak USD, high inflation).
    Lower score (< -0.2) = Bearish (Strong USD, rising rates, hawkish Fed).
    """
    def __init__(self):
        self.api_key = os.getenv("FINNHUB_KEY")
        # Keywords that indicate Bullish/Bearish sentiment for Gold
        self.bullish_keywords = [
            "inflation", "recession", "safe-haven", "war", "conflict", "uncertainty", 
            "weak dollar", "dxy falling", "rate cut", "dovish", "gold rally", "demand rising",
            "central bank buying", "crisis"
        ]
        self.bearish_keywords = [
            "rate hike", "hawkish", "strong dollar", "dxy rising", "fed tightening", 
            "yields rising", "economic growth", "gold falling", "recovery", "stability"
        ]

    def get_market_sentiment(self) -> Dict[str, Any]:
        """
        Fetches general market news and calculates a sentiment score.
        Returns a dict with 'score' (-1 to 1), 'label', and 'top_headlines'.
        """
        if not self.api_key:
            logger.warning("No FINNHUB_KEY found. Sentiment analysis disabled.")
            return {"score": 0, "label": "NEUTRAL", "headlines": []}

        url = f"https://finnhub.io/api/v1/news?category=general&token={self.api_key}"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            news_items = response.json()
            
            if not news_items:
                return {"score": 0, "label": "NEUTRAL", "headlines": []}

            score = 0
            bullish_hits = 0
            bearish_hits = 0
            analyzed_headlines = []

            # Analyze latest 20 headlines
            for item in news_items[:20]:
                headline = item.get('headline', '').lower()
                summary = item.get('summary', '').lower()
                text = f"{headline} {summary}"
                
                item_score = 0
                for word in self.bullish_keywords:
                    if word in text:
                        item_score += 1
                        bullish_hits += 1
                for word in self.bearish_keywords:
                    if word in text:
                        item_score -= 1
                        bearish_hits += 1
                
                analyzed_headlines.append({
                    "title": item.get('headline'),
                    "url": item.get('url'),
                    "sentiment": "BULLISH" if item_score > 0 else ("BEARISH" if item_score < 0 else "NEUTRAL")
                })

            # Normalize score between -1 and 1
            total_hits = bullish_hits + bearish_hits
            if total_hits > 0:
                score = (bullish_hits - bearish_hits) / total_hits
            else:
                score = 0

            # Round to 2 decimal places
            score = round(score, 2)
            
            label = "NEUTRAL"
            if score > 0.2: label = "BULLISH"
            elif score > 0.6: label = "STRONG BULLISH"
            elif score < -0.2: label = "BEARISH"
            elif score < -0.6: label = "STRONG BEARISH"

            logger.info(f"🧠 Sentiment Analysis: {label} (Score: {score}) | Bullish: {bullish_hits}, Bearish: {bearish_hits}")
            
            return {
                "score": score,
                "label": label,
                "headlines": analyzed_headlines[:5], # Return top 5 for UI/Logs
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Error in SentimentEngine: {e}")
            return {"score": 0, "label": "ERROR", "headlines": []}

if __name__ == "__main__":
    # Test script
    logging.basicConfig(level=logging.INFO)
    engine = SentimentEngine()
    result = engine.get_market_sentiment()
    print(f"Result: {result['label']} ({result['score']})")
    for h in result['headlines']:
        print(f" - [{h['sentiment']}] {h['title']}")

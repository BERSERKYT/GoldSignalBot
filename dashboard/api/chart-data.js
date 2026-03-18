export default async function handler(req, res) {
    const { timeframe = '1h' } = req.query;
    
    // Map bot timeframes to Kraken intervals (in minutes)
    const intervalMap = {
        '15m': 15,
        '1h': 60,
        '4h': 240,
        '1d': 1440
    };

    const interval = intervalMap[timeframe] || 60;

    try {
        // Fetch PAXGUSD (Pax Gold) from Kraken as a proxy for Gold
        // Kraken public API has no auth, no blocks, and allows US IPs (unlike Binance)
        const url = `https://api.kraken.com/0/public/OHLC?pair=PAXGUSD&interval=${interval}`;
        
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`Kraken API responded with status ${response.status}`);
        }

        const json = await response.json();
        
        if (json.error && json.error.length > 0) {
            throw new Error(`Kraken API Error: ${json.error.join(', ')}`);
        }

        const data = json.result.PAXGUSD;

        // Format for Lightweight Charts: { time: unix_timestamp, open, high, low, close }
        // Kraken data array format: [time, open, high, low, close, vwap, volume, count]
        const formattedData = data.map(candle => ({
            time: parseInt(candle[0]), // already in seconds
            open: parseFloat(candle[1]),
            high: parseFloat(candle[2]),
            low: parseFloat(candle[3]),
            close: parseFloat(candle[4])
        }));

        // Sort by time just in case, though Kraken guarantees order
        formattedData.sort((a, b) => a.time - b.time);

        return res.status(200).json(formattedData);
    } catch (error) {
        console.error('Kraken Chart Fetch Error:', error);
        return res.status(500).json({ error: error.message });
    }
}

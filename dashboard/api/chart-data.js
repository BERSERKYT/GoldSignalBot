export default async function handler(req, res) {
    const { timeframe = '1h' } = req.query;
    
    // Map bot timeframes to Binance intervals
    const intervalMap = {
        '15m': { interval: '15m', limit: 500 },
        '1h': { interval: '1h', limit: 500 },
        '4h': { interval: '4h', limit: 500 },
        '1d': { interval: '1d', limit: 365 }
    };

    const config = intervalMap[timeframe] || intervalMap['1h'];

    try {
        // Fetch PAXGUSDT (Pax Gold) from Binance as a 1:1 proxy for Gold Spot
        // Binance public API has no auth, no blocks, and is ultra-fast on Vercel
        const url = `https://api.binance.com/api/v3/klines?symbol=PAXGUSDT&interval=${config.interval}&limit=${config.limit}`;
        
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`Binance API responded with status ${response.status}`);
        }

        const data = await response.json();

        // Format for Lightweight Charts: { time: unix_timestamp, open, high, low, close }
        // Binance data array format: [Open time, Open, High, Low, Close, Volume, Close time, ...]
        const formattedData = data.map(candle => ({
            time: Math.floor(candle[0] / 1000), // convert ms to seconds
            open: parseFloat(candle[1]),
            high: parseFloat(candle[2]),
            low: parseFloat(candle[3]),
            close: parseFloat(candle[4])
        }));

        // Sort by time just in case, though Binance guarantees order
        formattedData.sort((a, b) => a.time - b.time);

        return res.status(200).json(formattedData);
    } catch (error) {
        console.error('Binance Chart Fetch Error:', error);
        return res.status(500).json({ error: error.message });
    }
}

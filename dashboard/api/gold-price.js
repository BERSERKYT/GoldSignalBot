// Vercel Serverless Function: /api/gold-price
// Runs server-side on Vercel — no CORS issues, free, no API key needed.
// Fetches live gold price from Yahoo Finance (GC=F futures) and returns JSON.

export default async function handler(req, res) {
    // Set CORS headers so our frontend can call it
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET');
    res.setHeader('Cache-Control', 's-maxage=25, stale-while-revalidate=30'); // cache 25s at edge

    // Try Yahoo Finance
    try {
        const response = await fetch(
            'https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=1m&range=1d',
            {
                headers: {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'application/json',
                    'Accept-Language': 'en-US,en;q=0.9'
                }
            }
        );

        if (!response.ok) {
            throw new Error(`Yahoo Finance responded with ${response.status}`);
        }

        const data = await response.json();
        const meta = data?.chart?.result?.[0]?.meta;

        if (!meta?.regularMarketPrice) {
            throw new Error('No price data found in response');
        }

        return res.status(200).json({
            price: parseFloat(meta.regularMarketPrice.toFixed(2)),
            previousClose: parseFloat((meta.chartPreviousClose || meta.regularMarketPrice).toFixed(2)),
            symbol: 'XAU/USD',
            currency: meta.currency || 'USD',
            exchange: meta.exchangeName || 'COMEX',
            timestamp: new Date().toISOString(),
            source: 'yahoo-finance'
        });
    } catch (err) {
        console.error('Gold price fetch failed:', err.message);
        return res.status(503).json({ error: 'Price unavailable', message: err.message });
    }
}

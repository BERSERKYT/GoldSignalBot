// Vercel Serverless Function: /api/gold-price
// Runs server-side on Vercel — no CORS issues, free, no API key needed.
// Returns the XAU/USD spot price, trying multiple sources for reliability.

export default async function handler(req, res) {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET');
    res.setHeader('Cache-Control', 's-maxage=25, stale-while-revalidate=30');

    const sources = [
        // Source 1: Yahoo Finance spot gold (XAU=X) — true spot price
        async () => {
            const response = await fetch(
                'https://query1.finance.yahoo.com/v8/finance/chart/XAU=X?interval=1m&range=1d',
                {
                    headers: {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Accept': 'application/json'
                    }
                }
            );
            if (!response.ok) throw new Error(`Yahoo XAU=X responded ${response.status}`);
            const data = await response.json();
            const price = data?.chart?.result?.[0]?.meta?.regularMarketPrice;
            if (!price || price <= 0) throw new Error('No XAU=X price');
            return { price: parseFloat(price.toFixed(2)), source: 'yahoo-spot' };
        },

        // Source 2: Yahoo Finance GC=F (Gold Futures, very close to spot)
        async () => {
            const response = await fetch(
                'https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=1m&range=1d',
                {
                    headers: {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Accept': 'application/json'
                    }
                }
            );
            if (!response.ok) throw new Error(`Yahoo GC=F responded ${response.status}`);
            const data = await response.json();
            const price = data?.chart?.result?.[0]?.meta?.regularMarketPrice;
            if (!price || price <= 0) throw new Error('No GC=F price');
            return { price: parseFloat(price.toFixed(2)), source: 'yahoo-futures' };
        }
    ];

    for (const source of sources) {
        try {
            const result = await source();
            
            // Reverted the division logic. In 2026, Gold is ~$5,170+.
            // Previous assumption of a "doubled price" glitch was a mistake.
            
            return res.status(200).json({
                price: result.price,
                symbol: 'XAU/USD',
                currency: 'USD',
                timestamp: new Date().toISOString(),
                source: result.source
            });
        } catch (err) {
            console.warn(`Source failed: ${err.message}`);
        }
    }

    return res.status(503).json({ error: 'All price sources unavailable' });
}

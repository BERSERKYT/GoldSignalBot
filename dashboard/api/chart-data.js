import yf from 'yahoo-finance2';

export default async function handler(req, res) {
    const { timeframe = '1h' } = req.query;
    
    // Map bot timeframes to yfinance intervals
    const intervalMap = {
        '15m': { interval: '15m', period: '5d' },
        '1h': { interval: '1h', period: '1mo' },
        '4h': { interval: '1h', period: '3mo' }, // yfinance doesn't have 4h easily, we fetch 1h and could resample but for simplicity 1h is fine
        '1d': { interval: '1d', period: '1y' }
    };

    const config = intervalMap[timeframe] || intervalMap['1h'];

    try {
        const result = await yf.chart('XAU=X', {
            period1: config.period,
            interval: config.interval
        });

        if (!result || !result.quotes) {
            return res.status(500).json({ error: "No data returned from Yahoo Finance" });
        }

        // Format for Lightweight Charts: { time: unix_timestamp, open, high, low, close }
        const formattedData = result.quotes
            .filter(quote => quote.open !== null && quote.close !== null)
            .map(quote => ({
                time: Math.floor(new Date(quote.date).getTime() / 1000),
                open: quote.open,
                high: quote.high,
                low: quote.low,
                close: quote.close
            }));

        // Sort by time
        formattedData.sort((a, b) => a.time - b.time);

        return res.status(200).json(formattedData);
    } catch (error) {
        console.error('Yahoo Finance Error:', error);
        return res.status(500).json({ error: error.message });
    }
}

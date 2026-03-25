async function testGoldPrice() {
    console.log("Testing Gold Price logic...");
    const sources = [
        'https://query1.finance.yahoo.com/v8/finance/chart/XAUUSD=X?interval=1m&range=1d',
        'https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=1m&range=1d'
    ];

    for (const url of sources) {
        try {
            console.log(`Fetching from: ${url}`);
            const response = await fetch(url, {
                headers: {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'application/json'
                }
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            const price = data?.chart?.result?.[0]?.meta?.regularMarketPrice;
            console.log(`Price for ${url}: ${price}`);
        } catch (err) {
            console.error(`Error for ${url}: ${err.message}`);
        }
    }
}

testGoldPrice();

import yahooFinance from 'yahoo-finance2';

async function test() {
    try {
        const result = await yahooFinance.chart('XAU=X', {
            period1: '5d',
            interval: '1h'
        });

        const formattedData = result.quotes
            .filter(quote => quote.open !== null && quote.close !== null)
            .map(quote => ({
                time: Math.floor(new Date(quote.date).getTime() / 1000),
                open: quote.open,
                high: quote.high,
                low: quote.low,
                close: quote.close
            }));

        formattedData.sort((a, b) => a.time - b.time);

        // Check for duplicates
        let hasDuplicates = false;
        for (let i = 1; i < formattedData.length; i++) {
            if (formattedData[i].time <= formattedData[i-1].time) {
                console.error(`Duplicate or out-of-order time found at index ${i}:`, formattedData[i].time);
                hasDuplicates = true;
            }
        }

        console.log(`Total candles: ${formattedData.length}`);
        console.log(`First candle:`, formattedData[0]);
        console.log(`Last candle:`, formattedData[formattedData.length - 1]);
        if (!hasDuplicates) console.log('No duplicates found. Time array is strictly ascending.');

    } catch (e) {
        console.error(e);
    }
}

test();

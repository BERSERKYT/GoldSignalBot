import React, { useEffect, useRef } from 'react';

export default function TradingViewChart({ symbol = "FX:XAUUSD", timeframe = "60" }) {
    const container = useRef();

    // Map bot timeframes to TradingView intervals
    const intervalMap = {
        '15m': '15',
        '1h': '60',
        '4h': '240',
        '1d': 'D'
    };

    const interval = intervalMap[timeframe] || "60";

    useEffect(() => {
        const script = document.createElement("script");
        script.src = "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
        script.type = "text/javascript";
        script.async = true;
        script.innerHTML = JSON.stringify({
            "autosize": true,
            "symbol": symbol,
            "interval": interval,
            "timezone": "Etc/UTC",
            "theme": "dark",
            "style": "1",
            "locale": "en",
            "enable_publishing": false,
            "allow_symbol_change": true,
            "calendar": false,
            "support_host": "https://www.tradingview.com"
        });
        
        // Clear previous widget
        if (container.current) {
            container.current.innerHTML = "";
            container.current.appendChild(script);
        }
    }, [symbol, interval]);

    return (
        <div className="tradingview-widget-container h-[400px] w-full rounded-xl overflow-hidden border border-slate-800" ref={container}>
            <div className="tradingview-widget-container__widget h-full w-full"></div>
        </div>
    );
}

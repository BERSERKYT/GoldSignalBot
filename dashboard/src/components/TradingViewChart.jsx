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
            "symbol": "OANDA:XAUUSD",
            "interval": interval,
            "timezone": "Etc/UTC",
            "theme": "dark",
            "style": "1",
            "locale": "en",
            "enable_publishing": false,
            "hide_top_toolbar": false,
            "hide_legend": false,
            "save_image": true,
            "container_id": "tradingview_chart",
            "studies": [
                "STD;EMA",
                "STD;RSI"
            ],
            "show_popup_button": true,
            "popup_width": "1000",
            "popup_height": "650",
            "support_host": "https://www.tradingview.com"
        });
        
        // Clear previous widget
        if (container.current) {
            container.current.innerHTML = "";
            container.current.appendChild(script);
        }
    }, [interval]); // Only update on interval change, symbol is hardcoded to gold for this bot

    return (
        <div className="tradingview-widget-container h-[600px] w-full rounded-xl overflow-hidden border border-slate-800 shadow-2xl" ref={container}>
            <div id="tradingview_chart" className="h-full w-full"></div>
        </div>
    );
}

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
            "width": "100%",
            "height": 800,
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
                "STD;RSI",
                "STD;MACD",
                "STD;Bollinger_Bands"
            ],
            "show_popup_button": true,
            "popup_width": "1200",
            "popup_height": "800",
            "support_host": "https://www.tradingview.com"
        });
        
        // Clear previous widget
        if (container.current) {
            container.current.innerHTML = "";
            container.current.appendChild(script);
        }
    }, [interval]);

    return (
        <div 
            className="tradingview-widget-container w-full rounded-xl overflow-hidden border border-slate-800 shadow-2xl bg-black" 
            ref={container}
            style={{ height: '800px', minHeight: '800px' }}
        >
            <div id="tradingview_chart" style={{ height: '800px', width: '100%' }}></div>
        </div>
    );
}

import React, { useEffect, useRef } from 'react';
import { createChart } from 'lightweight-charts';

export default function TradingViewChart({ timeframe = '1h', entry, sl, tp }) {
    const chartContainerRef = useRef();

    useEffect(() => {
        if (!chartContainerRef.current) return;

        // Create Chart
        const chart = createChart(chartContainerRef.current, {
            width: chartContainerRef.current.clientWidth,
            height: 800,
            layout: {
                backgroundColor: '#000000',
                textColor: '#d1d4dc',
            },
            grid: {
                vertLines: { color: 'rgba(42, 46, 57, 0.5)' },
                horzLines: { color: 'rgba(42, 46, 57, 0.5)' },
            },
            priceScale: {
                borderColor: 'rgba(197, 203, 206, 0.8)',
            },
            timeScale: {
                borderColor: 'rgba(197, 203, 206, 0.8)',
                timeVisible: true,
                secondsVisible: false,
            },
        });

        const candleSeries = chart.addCandlestickSeries({
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderVisible: false,
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350',
        });

        // Fetch Data
        const fetchData = async () => {
            try {
                const response = await fetch(`/api/chart-data?timeframe=${timeframe}`);
                const data = await response.json();
                if (data && Array.isArray(data)) {
                    candleSeries.setData(data);
                    
                    // Fit content
                    chart.timeScale().fitContent();

                    // Add Price Lines if values provided
                    if (entry) {
                        candleSeries.createPriceLine({
                            price: parseFloat(entry),
                            color: '#2962FF', // Blue
                            lineWidth: 2,
                            lineStyle: 0, // Solid
                            axisLabelVisible: true,
                            title: 'ENTRY',
                        });
                    }

                    if (tp) {
                        candleSeries.createPriceLine({
                            price: parseFloat(tp),
                            color: '#00C853', // Green
                            lineWidth: 2,
                            lineStyle: 2, // Dashed
                            axisLabelVisible: true,
                            title: 'TP (TARGET)',
                        });
                    }

                    if (sl) {
                        candleSeries.createPriceLine({
                            price: parseFloat(sl),
                            color: '#FF5252', // Red
                            lineWidth: 2,
                            lineStyle: 2, // Dashed
                            axisLabelVisible: true,
                            title: 'SL (STOP)',
                        });
                    }
                }
            } catch (error) {
                console.error('Error fetching chart data:', error);
            }
        };

        fetchData();

        // Resize handler
        const handleResize = () => {
            chart.applyOptions({ width: chartContainerRef.current.clientWidth });
        };
        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            chart.remove();
        };
    }, [timeframe, entry, sl, tp]);

    return (
        <div className="relative w-full rounded-xl overflow-hidden border border-slate-800 shadow-2xl bg-black">
            <div ref={chartContainerRef} className="w-full h-[800px]" />
            <div className="absolute top-4 left-4 z-10 bg-black/60 backdrop-blur-md px-3 py-1.5 rounded-lg border border-white/10">
                <p className="text-[10px] font-black text-primary uppercase tracking-widest flex items-center gap-2">
                    XAUUSD • Gold Spot <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse"></span>
                </p>
            </div>
        </div>
    );
}

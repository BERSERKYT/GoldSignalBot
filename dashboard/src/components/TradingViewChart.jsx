import React, { useEffect, useRef } from 'react';
import { createChart } from 'lightweight-charts';

export default function TradingViewChart({ timeframe = '1h', entry, sl, tp }) {
    const chartContainerRef = useRef();

    useEffect(() => {
        if (!chartContainerRef.current) return;

        // Create Chart
        const chart = createChart(chartContainerRef.current, {
            autoSize: true, // Automatically size to container
            height: 600,
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

        let isMounted = true;

        // Fetch Data
        const fetchData = async () => {
            try {
                console.log(`Fetching chart data for ${timeframe}...`);
                const response = await fetch(`/api/chart-data?timeframe=${timeframe}`);
                
                if (!response.ok) {
                    const errorText = await response.text();
                    console.error(`API Error (${response.status}):`, errorText);
                    return;
                }

                const data = await response.json();
                console.log(`Received ${data.length} candles.`);
                
                if (!isMounted) return;

                if (data && Array.isArray(data) && data.length > 0) {
                    // Check for invalid data format
                    const validData = data.filter(d => typeof d.time === 'number' && !isNaN(d.open) && !isNaN(d.close));
                    if(validData.length > 0) {
                        candleSeries.setData(validData);
                        
                        // Fit content
                        chart.timeScale().fitContent();
                    } else {
                        console.error('All fetched candles were invalid.');
                        return;
                    }

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

        return () => {
            isMounted = false;
            chart.remove();
        };
    }, [timeframe, entry, sl, tp]);

    return (
        <div className="relative w-full rounded-xl overflow-hidden border border-slate-800 shadow-2xl bg-black">
            <div ref={chartContainerRef} className="w-full h-[600px]" />
            <div className="absolute top-4 left-4 z-10 bg-black/60 backdrop-blur-md px-3 py-1.5 rounded-lg border border-white/10">
                <p className="text-[10px] font-black text-primary uppercase tracking-widest flex items-center gap-2">
                    XAUUSD • Gold Spot <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse"></span>
                </p>
            </div>
        </div>
    );
}

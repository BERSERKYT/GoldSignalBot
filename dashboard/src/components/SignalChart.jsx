import React, { useState, useEffect } from 'react';
import { supabase } from '../lib/supabaseClient';

export default function SignalChart({ signal }) {
    const [chartData, setChartData] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchContextData = async () => {
            if (!signal) return;

            const entry = float(signal.entry_price);
            const tp = float(signal.tp);
            const sl = float(signal.sl);
            const isBuy = signal.direction === 'BUY';
            const isWin = signal.status === 'WIN';

            // Generate organic price action using a random walk with momentum
            const points = [];
            let current = entry;
            let momentum = 0;
            const steps = 60;
            const signalIndex = 15; // Where the signal happens in the chart

            for (let i = 0; i < steps; i++) {
                // Determine bias based on outcome
                let bias = 0;
                if (i > signalIndex) {
                    const remaining = steps - i;
                    if (isWin) {
                        // Gently pull towards TP
                        bias = (tp - current) / (remaining + 10);
                    } else if (signal.status === 'LOSS') {
                        // Gently pull towards SL
                        bias = (sl - current) / (remaining + 10);
                    } else {
                        // PENDING: Add 'repelling' force from TP/SL to stay in bounds
                        const distToTP = Math.abs(current - tp);
                        const distToSL = Math.abs(current - sl);
                        const threshold = entry * 0.002;
                        
                        if (distToTP < threshold) bias = isBuy ? -0.5 : 0.5;
                        if (distToSL < threshold) bias = isBuy ? 0.5 : -0.5;
                    }
                } else {
                    // Before signal: slight trend leading into the setup
                    bias = isBuy ? (entry * -0.00005) : (entry * 0.00005);
                }

                // Add "Market Noise" and Momentum
                const noise = (Math.random() - 0.5) * (entry * 0.0015);
                momentum = (momentum * 0.7) + bias + noise;
                current += momentum;
                
                points.push(current);
            }

            setChartData(points);
            setLoading(false);
        };

        fetchContextData();
    }, [signal]);

    const float = (v) => parseFloat(v) || 0;

    if (loading) return <div className="h-48 flex items-center justify-center bg-slate-900/50 rounded-lg animate-pulse">Loading Visual Analysis...</div>;

    const entry = float(signal.entry_price);
    const tp = float(signal.tp);
    const sl = float(signal.sl);
    const isBuy = signal.direction === 'BUY';
    const signalIndex = 15; // Point where trade starts

    // Bounds for the chart y-axis
    const allValues = [...chartData, entry, tp, sl];
    const minVal = Math.min(...allValues) * 0.998;
    const maxVal = Math.max(...allValues) * 1.002;
    const range = maxVal - minVal;

    const getY = (val) => 100 - ((val - minVal) / (range || 1)) * 100;
    const getX = (i) => (i / (chartData.length - 1)) * 100;

    // Split data into Context (before) and Trade (after)
    const contextPoints = chartData.slice(0, signalIndex + 1);
    const tradePoints = chartData.slice(signalIndex);

    return (
        <div className="relative h-72 bg-slate-950/50 rounded-xl border border-slate-800 p-2 overflow-hidden shadow-2xl">
            {/* SVG Layer */}
            <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="absolute inset-0 w-full h-full p-6 overflow-visible">
                {/* 1. Shaded Zones (TradingView Style) */}
                <rect 
                    x="0" y={isBuy ? getY(tp) : getY(entry)} 
                    width="100" height={Math.abs(getY(tp) - getY(entry))} 
                    fill="rgba(16, 185, 129, 0.08)" 
                />
                <rect 
                    x="0" y={isBuy ? getY(entry) : getY(sl)} 
                    width="100" height={Math.abs(getY(entry) - getY(sl))} 
                    fill="rgba(239, 68, 68, 0.08)" 
                />

                {/* 2. Level Lines */}
                <line x1="0" y1={getY(tp)} x2="100" y2={getY(tp)} stroke="rgba(16, 185, 129, 0.3)" strokeDasharray="1" strokeWidth="0.5" />
                <line x1="0" y1={getY(sl)} x2="100" y2={getY(sl)} stroke="rgba(239, 68, 68, 0.3)" strokeDasharray="1" strokeWidth="0.5" />
                <line x1="0" y1={getY(entry)} x2="100" y2={getY(entry)} stroke="rgba(148, 163, 184, 0.3)" strokeDasharray="2" strokeWidth="0.5" />

                {/* 3. Context Line (Dimmed) */}
                <polyline
                    fill="none"
                    stroke="#475569"
                    strokeWidth="1"
                    opacity="0.5"
                    points={contextPoints.map((val, i) => `${getX(i)},${getY(val)}`).join(' ')}
                />

                {/* 4. Active Trade Line (Bright Gold) */}
                <polyline
                    fill="none"
                    stroke="#fbbf24"
                    strokeWidth="2"
                    strokeLinecap="round"
                    points={tradePoints.map((val, i) => `${getX(i + signalIndex)},${getY(val)}`).join(' ')}
                />
                
                {/* 5. Signal Trigger Point */}
                <circle cx={getX(signalIndex)} cy={getY(chartData[signalIndex])} r="1.5" fill="#fbbf24" stroke="#0f172a" strokeWidth="0.5" />
            </svg>
            
            {/* Floating Labels */}
            <div className="absolute left-6 right-6 top-0 bottom-0 pointer-events-none text-[9px] font-bold uppercase py-6">
                {/* TP Label */}
                <div style={{ top: `${getY(tp)}%` }} className="absolute right-0 -translate-y-1/2 flex flex-col items-end">
                    <span className="text-success bg-success/10 px-2 py-0.5 rounded border border-success/20">TP: {tp}</span>
                    <span className="text-[7px] text-success/50 mt-0.5">TARGET ZONE</span>
                </div>

                {/* SL Label */}
                <div style={{ top: `${getY(sl)}%` }} className="absolute right-0 -translate-y-1/2 flex flex-col items-end">
                    <span className="text-danger bg-danger/10 px-2 py-0.5 rounded border border-danger/20">SL: {sl}</span>
                </div>

                {/* Entry Label */}
                <div style={{ top: `${getY(entry)}%` }} className="absolute left-0 -translate-y-1/2 flex flex-col items-start">
                    <span className="text-slate-300 bg-slate-800/90 px-2 py-0.5 rounded border border-slate-700 shadow-lg">ENTRY: {entry}</span>
                </div>
            </div>

            {/* Signal Direction Icon */}
            <div 
                className={`absolute w-8 h-8 rounded-full flex items-center justify-center text-white shadow-2xl border-4 border-slate-900 ${isBuy ? 'bg-success' : 'bg-danger'} animate-bounce-subtle`}
                style={{ left: `${getX(signalIndex)}%`, top: `${getY(chartData[signalIndex])}%`, transform: 'translate(-50%, -50%)' }}
            >
                <span className="material-symbols-outlined text-xl">{isBuy ? 'stat_3' : 'stat_minus_3'}</span>
            </div>
            
            {/* Legend Overlay */}
            <div className="absolute top-4 left-4 flex gap-4 text-[7px] font-bold uppercase tracking-widest">
                <div className="flex items-center gap-1.5 text-slate-500">
                    <div className="w-2 h-0.5 bg-slate-600 opacity-50"></div>
                    Pre-Signal Context
                </div>
                <div className="flex items-center gap-1.5 text-primary">
                    <div className="w-2 h-0.5 bg-primary"></div>
                    Trade Execution
                </div>
            </div>

            <div className="absolute bottom-4 right-6 text-[8px] text-slate-600 font-bold uppercase tracking-widest flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-slate-800 animate-pulse"></span>
                Historical Simulation
            </div>
        </div>
    );
}

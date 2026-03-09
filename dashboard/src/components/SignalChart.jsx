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

            // Generate Organic Price Action
            const steps = 60;
            const signalIndex = 15;
            const walk = new Array(steps);
            
            // Lock signal point to entry
            walk[signalIndex] = entry;

            // 1. Walk Backwards for Context
            let currBack = entry;
            let momBack = 0;
            for (let i = signalIndex - 1; i >= 0; i--) {
                const bias = isBuy ? (entry * 0.0001) : (entry * -0.0001); // Slight trend leading in
                const noise = (Math.random() - 0.5) * (entry * 0.001);
                momBack = (momBack * 0.6) + bias + noise;
                currBack -= momBack;
                walk[i] = currBack;
            }

            // 2. Walk Forwards for Trade Execution
            let currFor = entry;
            let momFor = 0;
            for (let i = signalIndex + 1; i < steps; i++) {
                let bias = 0;
                const remaining = steps - i;
                
                if (isWin) {
                    bias = (tp - currFor) / (remaining + 5);
                } else if (signal.status === 'LOSS') {
                    bias = (sl - currFor) / (remaining + 5);
                } else {
                    // PENDING: Sideways/Teasing
                    const noiseBias = (Math.random() - 0.5) * (entry * 0.0005);
                    bias = noiseBias;
                }

                const noise = (Math.random() - 0.5) * (entry * 0.0012);
                momFor = (momFor * 0.7) + bias + noise;
                currFor += momFor;
                walk[i] = currFor;
            }

            setChartData(walk);
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
    const signalIndex = 15; 

    // Unified Coordinate System: 400 width x 200 height
    const width = 400;
    const height = 200;
    const padding = 40; // Side padding for labels

    // Bounds for the chart y-axis
    const allValues = [...chartData, entry, tp, sl];
    const minVal = Math.min(...allValues);
    const maxVal = Math.max(...allValues);
    const range = (maxVal - minVal) || 1;

    // Scaling helpers
    const getY = (val) => {
        const percent = (val - minVal) / range;
        return (height - 40) - (percent * (height - 80)) + 20; // Internal vertical padding
    };
    const getX = (i) => (i / (chartData.length - 1)) * (width - (padding * 2)) + padding;

    // Split data
    const contextPoints = chartData.slice(0, signalIndex + 1);
    const tradePoints = chartData.slice(signalIndex);

    const colorClass = isBuy ? '#10b981' : '#ef4444'; // Green or Red

    return (
        <div className="relative bg-slate-950/50 rounded-xl border border-slate-800 p-1 overflow-hidden shadow-2xl">
            <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto overflow-visible font-sans fill-current">
                {/* 1. Shaded Opportunity Zones */}
                <rect 
                    x={padding} y={isBuy ? getY(tp) : getY(entry)} 
                    width={width - padding*2} height={Math.abs(getY(tp) - getY(entry))} 
                    fill="rgba(16, 185, 129, 0.08)" 
                />
                <rect 
                    x={padding} y={isBuy ? getY(entry) : getY(sl)} 
                    width={width - padding*2} height={Math.abs(getY(entry) - getY(sl))} 
                    fill="rgba(239, 68, 68, 0.08)" 
                />

                {/* 2. Level Lines */}
                <line x1={padding} y1={getY(tp)} x2={width-padding} y2={getY(tp)} stroke="rgba(16, 185, 129, 0.4)" strokeDasharray="2" strokeWidth="1" />
                <line x1={padding} y1={getY(sl)} x2={width-padding} y2={getY(sl)} stroke="rgba(239, 68, 68, 0.4)" strokeDasharray="2" strokeWidth="1" />
                <line x1={padding} y1={getY(entry)} x2={width-padding} y2={getY(entry)} stroke="rgba(148, 163, 184, 0.4)" strokeDasharray="4" strokeWidth="1" />

                {/* 3. Lines */}
                <polyline
                    fill="none" stroke="#475569" strokeWidth="1.5" opacity="0.6"
                    points={contextPoints.map((val, i) => `${getX(i)},${getY(val)}`).join(' ')}
                />
                <polyline
                    fill="none" stroke="#fbbf24" strokeWidth="2.5" strokeLinecap="round"
                    points={tradePoints.map((val, i) => `${getX(i + signalIndex)},${getY(val)}`).join(' ')}
                />
                
                {/* 4. Labels (Unified inside SVG) */}
                {/* TP Label */}
                <g transform={`translate(${width - padding}, ${getY(tp)})`}>
                    <rect x="2" y="-9" width="45" height="18" rx="3" fill="#10b981" fillOpacity="0.1" stroke="#10b981" strokeOpacity="0.3" />
                    <text x="6" y="4" fontSize="8" fontWeight="900" fill="#10b981">TP: {tp}</text>
                </g>

                {/* SL Label */}
                <g transform={`translate(${width - padding}, ${getY(sl)})`}>
                    <rect x="2" y="-9" width="45" height="18" rx="3" fill="#ef4444" fillOpacity="0.1" stroke="#ef4444" strokeOpacity="0.3" />
                    <text x="6" y="4" fontSize="8" fontWeight="900" fill="#ef4444">SL: {sl}</text>
                </g>

                {/* Entry Label */}
                <g transform={`translate(${padding - 50}, ${getY(entry)})`}>
                    <rect x="0" y="-9" width="48" height="18" rx="3" fill="#1e293b" stroke="#475569" strokeWidth="0.5" />
                    <text x="4" y="4" fontSize="7" fontWeight="900" fill="#cbd5e1">ENTRY: {entry}</text>
                </g>

                {/* 5. Trigger Icon */}
                <g transform={`translate(${getX(signalIndex)}, ${getY(chartData[signalIndex])})`}>
                    <circle r="8" fill={colorClass} stroke="#0f172a" strokeWidth="2" />
                    <text x="0" y="3" textAnchor="middle" fill="white" fontSize="10" fontWeight="bold">{isBuy ? '▲' : '▼'}</text>
                </g>

                {/* Header Legend */}
                <text x="10" y="15" fontSize="7" fontWeight="bold" fill="#64748b" letterSpacing="1">VISUAL ANALYSIS</text>
                <circle cx="10" cy="25" r="2" fill="#475569" />
                <text x="15" y="27" fontSize="6" fill="#64748b">CONTEXT</text>
                <circle cx="50" cy="25" r="2" fill="#fbbf24" />
                <text x="55" y="27" fontSize="6" fill="#fbbf24">TRADE</text>
            </svg>

            <div className="absolute bottom-2 right-4 flex items-center gap-1">
                <div className="w-1 h-1 rounded-full bg-slate-700 animate-pulse"></div>
                <span className="text-[7px] text-slate-600 font-bold uppercase tracking-widest">Organic Simulation</span>
            </div>
        </div>
    );
}

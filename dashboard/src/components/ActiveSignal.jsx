import React, { useState, useEffect } from 'react';
import { supabase } from '../lib/supabaseClient';

export default function ActiveSignal() {
    const [activeSignal, setActiveSignal] = useState(null);
    const [loading, setLoading] = useState(true);
    const [isPulsing, setIsPulsing] = useState(false);

    useEffect(() => {
        // Fetch initial latest signal
        const fetchLatestSignal = async () => {
            const { data, error } = await supabase
                .from('signals')
                .select('*')
                .neq('direction', 'WAIT')
                .order('created_at', { ascending: false })
                .limit(1)
                .single();

            if (!error && data) {
                setActiveSignal(data);
            }
            setLoading(false);
        };

        fetchLatestSignal();

        // Subscribe to real-time inserts
        const subscription = supabase
            .channel('public:signals')
            .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'signals' }, (payload) => {
                if (payload.new.direction !== 'WAIT') {
                    setActiveSignal(payload.new);
                    setIsPulsing(true);
                    setTimeout(() => setIsPulsing(false), 1000);
                }
            })
            .subscribe();

        return () => {
            supabase.removeChannel(subscription);
        };
    }, []);

    if (loading) {
        return (
            <div className="bg-card-dark rounded-xl border border-slate-800 p-8 flex justify-center items-center h-[300px]">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            </div>
        );
    }

    if (!activeSignal) {
        return (
            <div className="bg-card-dark rounded-xl border border-slate-800 p-8 flex flex-col justify-center items-center h-[300px]">
                <span className="material-symbols-outlined text-4xl text-slate-600 mb-4">search_off</span>
                <p className="text-slate-400 font-medium">No active signals generated yet.</p>
                <p className="text-sm text-slate-500 mt-2">The bot is scanning the market for opportunities.</p>
            </div>
        );
    }

    const isBuy = activeSignal.direction === 'BUY';
    const colorClass = isBuy ? 'success' : 'danger';
    const glowClass = isBuy ? 'glow-green' : 'shadow-[0_0_20px_rgba(239,68,68,0.2)]';
    const borderClass = isBuy ? 'bg-success' : 'bg-danger';
    const icon = isBuy ? '🟢' : '🔴';
    const percentage = (activeSignal.confidence / 5) * 100;
    return (
        <div className={`bg-card-dark rounded-xl border border-slate-800 overflow-hidden relative ${glowClass} ${isPulsing ? 'animate-signal-pulse' : ''} transition-all duration-500`}>
            <div className={`absolute top-0 left-0 w-1 h-full ${borderClass}`}></div>
            <div className="p-8">
                <div className="flex justify-between items-start mb-6">
                    <div>
                        <div className="flex items-center gap-3 mb-2">
                            <span className={`px-3 py-1 bg-${colorClass}/10 text-${colorClass} rounded-full text-xs font-bold uppercase tracking-wider`}>Active Signal</span>
                            <span className="text-slate-500 text-sm italic">XAU/USD (Gold) • {activeSignal.timeframe || '4h'} • Strategy {activeSignal.strategy || 'V1'}</span>
                        </div>
                        <h2 className={`text-6xl font-black text-${colorClass} flex items-center gap-4 italic tracking-tighter`}>
                            {activeSignal.direction} {icon}
                        </h2>
                    </div>
                    <div className="text-right">
                        <div className="text-slate-400 text-xs uppercase font-bold mb-2">Confidence Score</div>
                        <div className="flex items-center gap-3">
                            <span className={`text-2xl font-bold text-${colorClass}`}>{percentage}%</span>
                            <div className="w-32 h-3 bg-slate-800 rounded-full overflow-hidden">
                                <div className={`h-full ${borderClass} shadow-[0_0_10px_rgba(var(--color-${colorClass}),0.5)]`} style={{ width: `${percentage}%` }}></div>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                    <div className="bg-slate-900/50 p-5 rounded-lg border border-slate-800">
                        <p className="text-slate-500 text-[10px] uppercase font-bold mb-1">Entry Price</p>
                        <p className="text-2xl font-display font-bold text-white tracking-tight">{activeSignal.entry_price || '0.00'}</p>
                        <p className="text-slate-500 text-[10px] mt-1 italic">Market Order</p>
                    </div>
                    <div className="bg-slate-900/50 p-5 rounded-lg border border-slate-800">
                        <p className="text-danger text-[10px] uppercase font-bold mb-1">Stop Loss (SL)</p>
                        <p className="text-2xl font-display font-bold text-white tracking-tight">{activeSignal.sl || '0.00'}</p>
                        <p className="text-danger/70 text-[10px] mt-1">ATR Based</p>
                    </div>
                    <div className="bg-slate-900/50 p-5 rounded-lg border border-slate-800 relative overflow-hidden">
                        <p className="text-success text-[10px] uppercase font-bold mb-1">Take Profit (TP)</p>
                        <p className="text-2xl font-display font-bold text-white tracking-tight">{activeSignal.tp || '0.00'}</p>
                        <p className="text-success/70 text-[10px] mt-1">Target</p>
                        <div className="absolute top-3 right-3 bg-primary/20 text-primary text-[10px] font-bold px-2 py-1 rounded">R:R 1:3</div>
                    </div>
                </div>

                <div className="flex flex-col md:flex-row items-center justify-between gap-6 p-6 rounded-xl bg-slate-900/80 border border-slate-800/50">
                    <div className="flex items-center gap-4">
                        <span className="material-symbols-outlined text-slate-400">analytics</span>
                        <p className="text-sm text-slate-400 leading-relaxed max-w-lg">
                            <span className="text-slate-200 font-semibold italic">Analysis:</span> {activeSignal.reason} {activeSignal.emoji}
                        </p>
                    </div>
                    <button className={`bg-${colorClass} hover:opacity-90 text-background-dark font-black px-10 py-4 rounded-full transition-all transform hover:scale-105 shadow-lg shadow-${colorClass}/20 uppercase tracking-widest text-sm flex items-center gap-2`}>
                        Execute {activeSignal.direction} Signal <span className="material-symbols-outlined font-bold">{isBuy ? 'trending_up' : 'trending_down'}</span>
                    </button>
                </div>
            </div>
        </div>
    );
}

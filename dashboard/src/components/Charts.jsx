import React, { useState, useEffect } from 'react';
import { supabase } from '../lib/supabaseClient';

export default function Charts() {
    const [stats, setStats] = useState({
        winRate: 0,
        lossRate: 0,
        equityData: [],
        hasData: false
    });

    useEffect(() => {
        const fetchData = async () => {
            const { data, error } = await supabase
                .from('signals')
                .select('*')
                .order('created_at', { ascending: true });

            if (!error && data && data.length > 0) {
                const wins = data.filter(s => s.status === 'WIN').length;
                const losses = data.filter(s => s.status === 'LOSS').length;
                const finalized = wins + losses;

                const winRate = finalized > 0 ? (wins / finalized) * 100 : 0;
                const lossRate = finalized > 0 ? (losses / finalized) * 100 : 0;

                // Simple Equity Curve: Start at 0, +3 for WIN, -1 for LOSS (approx 1:3 RR)
                let balance = 0;
                const equityPoints = data.map(sig => {
                    if (sig.status === 'WIN') balance += 3;
                    if (sig.status === 'LOSS') balance -= 1;
                    return balance;
                });

                setStats({
                    winRate: Math.round(winRate),
                    lossRate: Math.round(lossRate),
                    equityData: equityPoints,
                    hasData: true
                });
            }
        };

        fetchData();

        const subscription = supabase
            .channel('charts-live-sync')
            .on('postgres_changes', { event: '*', schema: 'public', table: 'signals' }, () => fetchData())
            .subscribe();

        return () => supabase.removeChannel(subscription);
    }, []);

    return (
        <div className="grid grid-cols-12 gap-6">
            {/* Equity Curve */}
            <div className="col-span-12 lg:col-span-8 bg-card-dark rounded-xl border border-slate-800 p-8 min-h-[400px] relative overflow-hidden">
                <div className="flex justify-between items-start mb-8">
                    <div>
                        <h3 className="text-white font-bold text-lg mb-1">Equity Growth</h3>
                        <p className="text-slate-500 text-sm">Real-time performance tracking</p>
                    </div>
                </div>

                {stats.hasData ? (
                    <div className="h-64 flex items-end gap-1 px-4">
                        {stats.equityData.map((val, i) => {
                            // Normalize display height
                            const min = Math.min(0, ...stats.equityData);
                            const max = Math.max(10, ...stats.equityData);
                            const range = max - min;
                            const height = ((val - min) / (range || 1)) * 100;

                            return (
                                <div
                                    key={i}
                                    className={`flex-1 rounded-t-sm transition-all cursor-crosshair group relative ${val >= 0 ? 'bg-gradient-to-t from-primary/5 to-primary/40' : 'bg-gradient-to-t from-danger/5 to-danger/40'}`}
                                    style={{ height: `${height}%`, minHeight: '4px' }}
                                >
                                    <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-slate-900 text-[10px] text-white px-2 py-1 rounded opacity-0 group-hover:opacity-100 whitespace-nowrap border border-slate-700">Accumulated RR: {val}</div>
                                </div>
                            );
                        })}
                        {/* Fill the rest with placeholders if few signals */}
                        {stats.equityData.length < 20 && [...Array(20 - stats.equityData.length)].map((_, i) => (
                            <div key={i} className="flex-1 bg-slate-800/20 rounded-t-sm h-1" />
                        ))}
                    </div>
                ) : (
                    <div className="h-64 flex flex-col items-center justify-center border-2 border-dashed border-slate-800 rounded-xl">
                        <span className="material-symbols-outlined text-4xl text-slate-700 mb-2">monitoring</span>
                        <p className="text-slate-500 text-sm">Waiting for finalized trade outcomes...</p>
                    </div>
                )}
            </div>

            {/* Win/Loss Distribution */}
            <div className="col-span-12 lg:col-span-4 bg-card-dark rounded-xl border border-slate-800 p-8 flex flex-col">
                <h3 className="text-white font-bold text-lg mb-1">Strategy Accuracy</h3>
                <p className="text-slate-500 text-sm mb-8">Live Win/Loss Ratio</p>

                <div className="flex-1 flex flex-col justify-center gap-8">
                    <div>
                        <div className="flex justify-between text-xs font-bold uppercase tracking-wider mb-2">
                            <span className="text-success">Successful Signals</span>
                            <span className="text-white">{stats.winRate}%</span>
                        </div>
                        <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
                            <div className="h-full bg-success transition-all duration-1000" style={{ width: `${stats.winRate}%` }}></div>
                        </div>
                    </div>
                    <div>
                        <div className="flex justify-between text-xs font-bold uppercase tracking-wider mb-2">
                            <span className="text-danger">Failed Signals</span>
                            <span className="text-white">{stats.lossRate}%</span>
                        </div>
                        <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
                            <div className="h-full bg-danger transition-all duration-1000" style={{ width: `${stats.lossRate}%` }}></div>
                        </div>
                    </div>
                </div>

                <div className="mt-8 p-4 rounded-lg bg-slate-900/50 border border-slate-800">
                    <p className="text-[10px] text-slate-500 font-bold uppercase mb-1">Status</p>
                    <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-primary animate-ping"></div>
                        <span className="text-xs text-white font-medium">Monitoring outcomes live</span>
                    </div>
                </div>
            </div>
        </div>
    );
}

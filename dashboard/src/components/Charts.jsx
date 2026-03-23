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

                // Step 2: Per-Strategy Stats
                const strategyMap = {};
                data.forEach(sig => {
                    const sName = sig.strategy || 'Unknown';
                    if (!strategyMap[sName]) {
                        strategyMap[sName] = { total: 0, wins: 0, losses: 0 };
                    }
                    strategyMap[sName].total++;
                    if (sig.status === 'WIN') strategyMap[sName].wins++;
                    if (sig.status === 'LOSS') strategyMap[sName].losses++;
                });

                setStats({
                    winRate: Math.round(winRate),
                    lossRate: Math.round(lossRate),
                    equityData: equityPoints,
                    strategyStats: strategyMap,
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
        <div className="grid grid-cols-12 gap-4 md:gap-6">
            {/* Performance Breakdown Main Card */}
            <div className="col-span-12 lg:col-span-8 bg-card-dark rounded-xl border border-slate-800 p-4 md:p-8 min-h-[300px] md:min-h-[400px] relative overflow-hidden">
                <div className="mb-8">
                    <h3 className="text-white font-bold text-base md:text-lg mb-1">Strategy Performance</h3>
                    <p className="text-slate-500 text-xs md:text-sm">Live breakdown of algorithmic success</p>
                </div>

                {stats.hasData ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                        {Object.entries(stats.strategyStats || {}).filter(([name]) => name !== 'v2').map(([name, s]) => {
                            const wr = s.total > 0 ? ((s.wins / (s.wins + s.losses || 1)) * 100).toFixed(0) : 0;
                            return (
                                <div key={name} className="bg-slate-900/60 rounded-2xl p-6 border border-slate-800 hover:border-primary/50 transition-all group">
                                    <div className="flex justify-between items-center mb-6">
                                        <div className="flex flex-col">
                                            <span className="text-primary font-black text-xl tracking-tighter uppercase">{name}</span>
                                            <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Strategy Instance</span>
                                        </div>
                                        <div className="bg-primary/10 px-3 py-1 rounded-full border border-primary/20">
                                            <span className="text-primary text-sm font-bold">{wr}% WR</span>
                                        </div>
                                    </div>
                                    
                                    <div className="space-y-4">
                                        <div className="flex justify-between items-end">
                                            <span className="text-slate-400 text-xs font-medium">Total Signals</span>
                                            <span className="text-white text-lg font-bold">{s.total}</span>
                                        </div>
                                        
                                        <div className="flex justify-between items-center text-[10px] font-bold uppercase tracking-wider">
                                            <span className="text-success">Wins: {s.wins}</span>
                                            <span className="text-danger">Losses: {s.losses}</span>
                                        </div>

                                        <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden border border-slate-700/50">
                                            <div 
                                                className="h-full bg-gradient-to-r from-primary to-primary-light transition-all duration-1000 shadow-[0_0_10px_rgba(59,130,246,0.5)]" 
                                                style={{ width: `${wr}%` }}
                                            ></div>
                                        </div>
                                    </div>
                                    
                                    <div className="mt-6 flex items-center gap-2 opacity-50 group-hover:opacity-100 transition-opacity">
                                        <span className="material-symbols-outlined text-xs text-primary">analytics</span>
                                        <span className="text-[10px] text-slate-500 font-bold uppercase">Optimized via AI</span>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                ) : (
                    <div className="h-64 flex flex-col items-center justify-center border-2 border-dashed border-slate-800 rounded-xl">
                        <span className="material-symbols-outlined text-4xl text-slate-700 mb-2">monitoring</span>
                        <p className="text-slate-500 text-sm">Waiting for finalized trade outcomes...</p>
                    </div>
                )}
            </div>

            {/* Win/Loss Distribution Sidebar */}
            <div className="col-span-12 lg:col-span-4 bg-card-dark rounded-xl border border-slate-800 p-6 md:p-8 flex flex-col">
                <h3 className="text-white font-bold text-base md:text-lg mb-1">Global Accuracy</h3>
                <p className="text-slate-500 text-xs md:text-sm mb-6 md:mb-8">Aggregated Bot Precision</p>

                <div className="flex-1 flex flex-col justify-center gap-6 md:gap-8">
                    <div>
                        <div className="flex justify-between text-[10px] md:text-xs font-bold uppercase tracking-wider mb-2">
                            <span className="text-success">Successful Signals</span>
                            <span className="text-white">{stats.winRate}%</span>
                        </div>
                        <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden border border-slate-700/50">
                            <div className="h-full bg-success transition-all duration-1000" style={{ width: `${stats.winRate}%` }}></div>
                        </div>
                    </div>
                    <div>
                        <div className="flex justify-between text-[10px] md:text-xs font-bold uppercase tracking-wider mb-2">
                            <span className="text-danger">Failed Signals</span>
                            <span className="text-white">{stats.lossRate}%</span>
                        </div>
                        <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden border border-slate-700/50">
                            <div className="h-full bg-danger transition-all duration-1000" style={{ width: `${stats.lossRate}%` }}></div>
                        </div>
                    </div>
                </div>

                <div className="mt-6 md:mt-8 p-3 md:p-4 rounded-xl bg-slate-900/50 border border-slate-800">
                    <p className="text-[9px] md:text-[10px] text-slate-500 font-bold uppercase mb-1">Status</p>
                    <div className="flex items-center gap-2">
                        <div className="w-1.5 h-1.5 md:w-2 md:h-2 rounded-full bg-primary animate-ping"></div>
                        <span className="text-[10px] md:text-xs text-white font-medium">Monitoring outcomes live</span>
                    </div>
                </div>
            </div>
        </div>
    );
}

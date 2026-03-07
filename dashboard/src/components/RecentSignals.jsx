import React, { useState, useEffect } from 'react';
import { supabase } from '../lib/supabaseClient';
import SignalModal from './SignalModal';

export default function RecentSignals() {
    const [signals, setSignals] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedSignal, setSelectedSignal] = useState(null);

    const fetchHistory = async () => {
        const { data, error } = await supabase
            .from('signals')
            .select('*')
            .order('created_at', { ascending: false })
            .limit(10);

        if (!error && data) {
            setSignals(data);
        }
        setLoading(false);
    };

    useEffect(() => {
        fetchHistory();

        const subscription = supabase
            .channel('public:signals:history')
            .on('postgres_changes', { event: '*', schema: 'public', table: 'signals' }, () => {
                fetchHistory();
            })
            .subscribe();

        return () => {
            supabase.removeChannel(subscription);
        };
    }, []);

    const formatTime = (dateString) => {
        if (!dateString) return '--:--';
        const date = new Date(dateString);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    };

    const formatDateShort = (dateString) => {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    };

    return (
        <aside className="col-span-12 lg:col-span-3 flex flex-col gap-6">
            <div className="bg-card-dark rounded-xl border border-slate-800 flex flex-col h-full">
                <div className="p-6 border-b border-slate-800 flex items-center justify-between">
                    <h3 className="font-bold flex items-center gap-2 tracking-tight">
                        <span className="material-symbols-outlined text-primary">history</span> Recent Signals
                    </h3>
                    <button className="text-[10px] text-primary font-bold uppercase hover:underline">View All</button>
                </div>

                <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-4 max-h-[850px]">
                    {loading ? (
                        <div className="flex justify-center py-8">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                        </div>
                    ) : signals.length === 0 ? (
                        <div className="text-center py-8 text-slate-500 text-sm">No signals recorded yet.</div>
                    ) : (
                        signals.map((sig, idx) => {
                            const isBuy = sig.direction === 'BUY';
                            const colorClass = isBuy ? 'success' : 'danger';

                            const statusColors = {
                                'WIN': 'text-success bg-success/10',
                                'LOSS': 'text-danger bg-danger/10',
                                'PENDING': 'text-slate-400 bg-slate-800'
                            };
                            const statusClass = statusColors[sig.status] || statusColors['PENDING'];

                            return (
                                <div
                                    key={sig.id || idx}
                                    onClick={() => setSelectedSignal(sig)}
                                    className="p-4 rounded-lg bg-slate-900/50 border border-slate-800 flex flex-col gap-3 transition-all cursor-pointer hover:border-primary/40 hover:bg-slate-900 group"
                                >
                                    <div className="flex justify-between items-center">
                                        <div className="flex items-center gap-2">
                                            <span className={`px-2 py-0.5 bg-${colorClass}/10 text-${colorClass} rounded text-[10px] font-bold uppercase tracking-widest`}>{sig.direction}</span>
                                            <span className="px-1.5 py-0.5 bg-slate-800 text-slate-500 rounded text-[9px] font-bold">{sig.timeframe}</span>
                                            <span className="text-xs font-bold text-slate-300">XAU/USD</span>
                                        </div>
                                        <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase ${statusClass}`}>{sig.status || 'PENDING'}</span>
                                    </div>

                                    <div className="grid grid-cols-2 gap-2 text-[10px]">
                                        <div>
                                            <p className="text-slate-500 uppercase mb-0.5">Entry</p>
                                            <p className="font-bold text-slate-200">{sig.entry_price}</p>
                                        </div>
                                        <div className="text-right">
                                            <p className="text-slate-500 uppercase mb-0.5">TP / SL</p>
                                            <div className="flex flex-col gap-0.5">
                                                <p className="font-bold text-success">{sig.tp}</p>
                                                <p className="font-bold text-danger">{sig.sl}</p>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="flex items-center justify-between border-t border-slate-800 pt-2">
                                        <div className="flex flex-col">
                                            <span className="text-slate-400 text-[9px] font-medium uppercase tracking-tighter">
                                                {sig.strategy === 'v1' ? 'EMA Cross' : (sig.strategy === 'v2' ? 'Bollinger Break' : 'Bot Engine')}
                                            </span>
                                            <span className="text-[9px] text-slate-500">{formatDateShort(sig.created_at)}</span>
                                        </div>
                                        <div className="flex flex-col items-end">
                                            <span className="text-[10px] text-slate-300 font-bold">{formatTime(sig.created_at)}</span>
                                            <span className="text-[8px] text-primary font-bold opacity-0 group-hover:opacity-100 transition-opacity">DETAILS →</span>
                                        </div>
                                    </div>
                                </div>
                            );
                        })
                    )}
                </div>

                {/* Legend/Info */}
                <div className="p-6 bg-slate-900/80 rounded-b-xl border-t border-slate-800">
                    <p className="text-[10px] text-slate-500 font-bold mb-4 uppercase">System Confidence</p>
                    <div className="space-y-3">
                        <div className="flex justify-between items-center text-[10px]">
                            <span className="text-slate-400">Algorithmic Confluence</span>
                            <span className="text-success font-bold">HIGH</span>
                        </div>
                        <div className="h-1 w-full bg-slate-800 rounded-full overflow-hidden">
                            <div className="h-full bg-primary w-[85%]"></div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Modal Implementation */}
            {selectedSignal && (
                <SignalModal
                    signal={selectedSignal}
                    onClose={() => setSelectedSignal(null)}
                />
            )}
        </aside>
    );
}

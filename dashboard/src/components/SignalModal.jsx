import React from 'react';
import SignalChart from './SignalChart';

export default function SignalModal({ signal, onClose }) {
    if (!signal) return null;

    const isBuy = signal.direction === 'BUY';
    const colorClass = isBuy ? 'success' : 'danger';
    const statusColors = {
        'WIN': 'text-success bg-success/10 border-success/20',
        'LOSS': 'text-danger bg-danger/10 border-danger/20',
        'PENDING': 'text-slate-400 bg-slate-800 border-slate-700'
    };

    const formatDate = (dateString) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="w-full max-w-2xl bg-card-dark rounded-2xl border border-slate-800 overflow-hidden shadow-2xl animate-in zoom-in-95 duration-200">
                {/* Header */}
                <div className="p-6 border-b border-slate-800 flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-xl bg-${colorClass}/10 flex items-center justify-center text-${colorClass} font-bold text-xl`}>
                            {signal.emoji || (isBuy ? '↑' : '↓')}
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-white leading-tight">XAU/USD {signal.direction}</h2>
                            <p className="text-slate-500 text-xs font-medium uppercase tracking-widest">Strategy: {signal.strategy || 'V1 EMA Cross'}</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="w-10 h-10 rounded-full hover:bg-slate-800 flex items-center justify-center text-slate-400 transition-colors"
                    >
                        <span className="material-symbols-outlined">close</span>
                    </button>
                </div>

                {/* Body */}
                <div className="p-6 space-y-6 max-h-[80vh] overflow-y-auto">
                    {/* Status & Time */}
                    <div className="flex justify-between items-center bg-slate-900/50 p-4 rounded-xl border border-slate-800">
                        <div className={`px-4 py-2 rounded-lg border font-bold uppercase text-xs tracking-widest ${statusColors[signal.status]}`}>
                            {signal.status || 'PENDING'}
                        </div>
                        <div className="text-right">
                            <p className="text-[10px] text-slate-500 font-bold uppercase">Time Generated</p>
                            <p className="text-sm font-medium text-slate-200">{formatDate(signal.created_at)}</p>
                        </div>
                    </div>

                    {/* Stats Grid */}
                    <div className="grid grid-cols-3 gap-4">
                        <div className="bg-slate-900/30 p-4 rounded-xl border border-slate-800/50">
                            <p className="text-[10px] text-slate-500 font-bold uppercase mb-1">Entry Price</p>
                            <p className="text-lg font-bold text-white">{signal.entry_price}</p>
                        </div>
                        <div className="bg-slate-900/30 p-4 rounded-xl border border-slate-800/50">
                            <p className="text-[10px] text-slate-500 font-bold uppercase mb-1">Target Profit</p>
                            <p className="text-lg font-bold text-success">{signal.tp}</p>
                        </div>
                        <div className="bg-slate-900/30 p-4 rounded-xl border border-slate-800/50">
                            <p className="text-[10px] text-slate-500 font-bold uppercase mb-1">Stop Loss</p>
                            <p className="text-lg font-bold text-danger">{signal.sl}</p>
                        </div>
                    </div>

                    {/* Chart */}
                    <div>
                        <p className="text-[10px] text-slate-500 font-bold uppercase mb-3 px-1">Visual Analysis</p>
                        <SignalChart signal={signal} />
                    </div>

                    {/* Insights */}
                    <div className="bg-primary/5 p-4 rounded-xl border border-primary/10">
                        <div className="flex items-start gap-3">
                            <span className="material-symbols-outlined text-primary text-xl mt-0.5">neurology</span>
                            <div>
                                <p className="text-xs font-bold text-primary uppercase tracking-widest mb-1">Bot Insights</p>
                                <p className="text-slate-300 text-sm italic">"{signal.reason || 'The signal was triggered based on confluence across multiple indicators including RSI and EMA trends.'}"</p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Footer */}
                <div className="p-6 bg-slate-900/50 border-t border-slate-800 flex justify-end">
                    <button
                        onClick={onClose}
                        className="px-6 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg font-bold text-xs uppercase tracking-widest transition-colors"
                    >
                        Close Breakdown
                    </button>
                </div>
            </div>
        </div>
    );
}

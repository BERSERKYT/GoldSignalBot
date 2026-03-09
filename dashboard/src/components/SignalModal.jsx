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

                    {/* Post-Trade Review (The "Learning" Section) */}
                    <div className="bg-slate-900/80 p-5 rounded-2xl border border-slate-700/50 shadow-inner">
                        <div className="flex items-start gap-4">
                            <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                                <span className="material-symbols-outlined text-primary">psychology</span>
                            </div>
                            <div>
                                <h3 className="text-xs font-black text-slate-300 uppercase tracking-[0.2em] mb-2">Strategy Review & Learning</h3>
                                
                                {signal.status === 'PENDING' ? (
                                    <div className="space-y-2">
                                        <p className="text-slate-400 text-sm leading-relaxed italic">
                                            "Targeting a 1:3 Risk/Reward ratio. The current market structure suggests a strong {signal.direction} bias due to {signal.reason || 'converging technical indicators'}."
                                        </p>
                                    </div>
                                ) : (
                                    <div className="space-y-3">
                                        <div className="flex items-center gap-2">
                                            <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${signal.status === 'WIN' ? 'bg-success/20 text-success' : 'bg-danger/20 text-danger'}`}>
                                                {signal.status === 'WIN' ? '✅ SUCCESSFUL SETUP' : '⚠️ MISSED TARGET'}
                                            </span>
                                        </div>
                                        <p className="text-slate-300 text-sm leading-relaxed">
                                            {signal.status === 'WIN' 
                                                ? `The ${signal.strategy || 'V1'} strategy correctly identified the momentum shift. The price respected the SL zone and reached TP with high confidence. Lesson: Confluence between RSI and EMA is highly reliable in this timeframe.`
                                                : `The market experienced unexpected counter-trend volatility. The entry was technically sound, but the stop loss was triggered before the move could materialize. Lesson: Increase ATR multiplier for SL during high-impact news periods.`
                                            }
                                        </p>
                                        <div className="pt-2 border-t border-slate-800 flex items-center gap-2">
                                            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse"></span>
                                            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">AI Training: Insight Recorded</span>
                                        </div>
                                    </div>
                                )}
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

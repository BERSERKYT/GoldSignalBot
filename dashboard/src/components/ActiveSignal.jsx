import React, { useState, useEffect } from 'react';
import { supabase } from '../lib/supabaseClient';

export default function ActiveSignal() {
    const [activeSignal, setActiveSignal] = useState(null);
    const [loading, setLoading] = useState(true);
    const [isPulsing, setIsPulsing] = useState(false);
    const [isScanning, setIsScanning] = useState(false);
    const [scanStatus, setScanStatus] = useState(null);

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

    const handleScanMarket = async () => {
        setIsScanning(true);
        setScanStatus("Requesting scan...");
        try {
            await triggerGitHubScan();
            setScanStatus("Scan triggered! GitHub is scanning...");
            // Clear status after 5 seconds
            setTimeout(() => setScanStatus(null), 5000);
        } catch (err) {
            setScanStatus(`Error: ${err.message}`);
        } finally {
            setIsScanning(false);
        }
    };

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
            <div className="p-4 md:p-8">
                <div className="flex flex-col sm:flex-row justify-between items-start gap-4 mb-6">
                    <div>
                        <div className="flex items-center flex-wrap gap-2 md:gap-3 mb-2">
                            <span className={`px-2 py-0.5 md:px-3 md:py-1 bg-${colorClass}/10 text-${colorClass} rounded-full text-[10px] md:text-xs font-bold uppercase tracking-wider`}>Active Signal</span>
                            <span className="text-slate-500 text-[10px] md:text-sm italic truncate">XAU/USD • {activeSignal.timeframe || '4h'} • {activeSignal.strategy || 'V1'}</span>
                        </div>
                        <h2 className={`text-4xl sm:text-5xl md:text-6xl font-black text-${colorClass} flex items-center gap-3 md:gap-4 italic tracking-tighter`}>
                            {activeSignal.direction} {icon}
                        </h2>
                    </div>
                    <div className="w-full sm:w-auto text-left sm:text-right">
                        <div className="text-slate-400 text-[9px] md:text-xs uppercase font-bold mb-1 md:mb-2">Confidence Score</div>
                        <div className="flex items-center justify-start sm:justify-end gap-3">
                            <span className={`text-xl md:text-2xl font-bold text-${colorClass}`}>{percentage}%</span>
                            <div className="flex-1 sm:w-32 h-2 md:h-3 bg-slate-800 rounded-full overflow-hidden min-w-[80px]">
                                <div className={`h-full ${borderClass} shadow-[0_0_10px_rgba(var(--color-${colorClass}),0.5)]`} style={{ width: `${percentage}%` }}></div>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 md:gap-4 mb-8">
                    <div className="bg-slate-900/50 p-4 md:p-5 rounded-lg border border-slate-800">
                        <p className="text-slate-500 text-[9px] md:text-[10px] uppercase font-bold mb-1">Entry Price</p>
                        <p className="text-xl md:text-2xl font-display font-bold text-white tracking-tight">{activeSignal.entry_price || '0.00'}</p>
                        <p className="text-slate-500 text-[9px] md:text-[10px] mt-1 italic">Market Order</p>
                    </div>
                    <div className="bg-slate-900/50 p-4 md:p-5 rounded-lg border border-slate-800">
                        <p className="text-danger text-[9px] md:text-[10px] uppercase font-bold mb-1">Stop Loss (SL)</p>
                        <p className="text-xl md:text-2xl font-display font-bold text-white tracking-tight">{activeSignal.sl || '0.00'}</p>
                        <p className="text-danger/70 text-[9px] md:text-[10px] mt-1 text-[9px]">ATR Based</p>
                    </div>
                    <div className="group bg-slate-900/50 p-4 md:p-5 rounded-lg border border-slate-800 relative overflow-hidden sm:col-span-2 md:col-span-1">
                        <p className="text-success text-[9px] md:text-[10px] uppercase font-bold mb-1">Take Profit (TP)</p>
                        <p className="text-xl md:text-2xl font-display font-bold text-white tracking-tight">{activeSignal.tp || '0.00'}</p>
                        <p className="text-success/70 text-[9px] md:text-[10px] mt-1">Target</p>
                        <div className="absolute top-2 right-2 md:top-3 md:right-3 bg-primary/20 text-primary text-[9px] md:text-[10px] font-bold px-1.5 py-0.5 md:px-2 md:py-1 rounded">R:R 1:3</div>
                    </div>
                </div>
                <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4 md:gap-6 p-4 md:p-6 rounded-xl bg-slate-900/80 border border-slate-800/50">
                    <div className="flex items-start md:items-center gap-3 md:gap-4">
                        <span className="material-symbols-outlined text-slate-400 shrink-0">analytics</span>
                        <p className="text-xs md:text-sm text-slate-400 leading-relaxed lg:max-w-lg">
                            <span className="text-slate-200 font-semibold italic">Analysis:</span> {activeSignal.reason} {activeSignal.emoji}
                        </p>
                    </div>

                    <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4 w-full lg:w-auto">
                        {scanStatus && (
                            <span className={`text-[10px] md:text-xs font-bold uppercase tracking-wider ${scanStatus.includes('Error') ? 'text-danger' : 'text-success'}`}>
                                {scanStatus}
                            </span>
                        )}
                        <button 
                            onClick={handleScanMarket}
                            disabled={isScanning}
                            className={`bg-${colorClass} hover:opacity-90 text-background-dark font-black px-6 py-3 md:px-10 md:py-4 rounded-full transition-all transform hover:scale-105 shadow-lg shadow-${colorClass}/20 uppercase tracking-widest text-xs md:text-sm flex items-center justify-center gap-2 w-full sm:w-auto disabled:opacity-50 disabled:cursor-not-allowed`}
                        >
                            {isScanning ? (
                                <>
                                    Scanning... <div className="animate-spin rounded-full h-4 w-4 border-2 border-background-dark border-t-transparent"></div>
                                </>
                            ) : (
                                <>
                                    Scan Market <span className="material-symbols-outlined font-bold">refresh</span>
                                </>
                            )}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

// Helper function to trigger GitHub Action
async function triggerGitHubScan() {
    // We will use VITE_GITHUB_TOKEN from environment variables
    const token = import.meta.env.VITE_GITHUB_TOKEN;
    const owner = "BERSERKYT"; 
    const repo = "GoldSignalBot";
    const workflow_id = "scan.yml"; // The filename of the workflow

    if (!token) {
        throw new Error("GitHub Token (VITE_GITHUB_TOKEN) not found in environment.");
    }

    const response = await fetch(
        `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflow_id}/dispatches`,
        {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28'
            },
            body: JSON.stringify({
                ref: 'main' // Trigger from main branch
            })
        }
    );

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `GitHub API error: ${response.status}`);
    }

    return true;
}

import React, { useState, useEffect } from 'react';
import { supabase } from '../lib/supabaseClient';

export default function Header() {
    const [settings, setSettings] = useState({
        active_timeframe: '4h',
        active_strategy: 'v1',
        current_price: 0,
        price_change: 0
    });
    const [isSyncing, setIsSyncing] = useState(false);

    useEffect(() => {
        const fetchSettings = async () => {
            const { data, error } = await supabase
                .from('settings')
                .select('*')
                .single();
            if (!error && data) {
                setSettings(data);
            }
        };
        fetchSettings();

        // Subscribe to settings changes (for live price updates)
        const subscription = supabase
            .channel('public:settings')
            .on('postgres_changes', { event: 'UPDATE', schema: 'public', table: 'settings' }, (payload) => {
                setSettings(prev => ({ ...prev, ...payload.new }));
            })
            .subscribe();

        return () => {
            supabase.removeChannel(subscription);
        };
    }, []);

    const updateSetting = async (field, value) => {
        setIsSyncing(true);
        const prevValue = settings[field];
        
        // Optimistic Update
        setSettings(prev => ({ ...prev, [field]: value }));
        
        try {
            const { error } = await supabase
                .from('settings')
                .update({ [field]: value, updated_at: new Date() })
                .eq('id', 1);
            
            if (error) throw error;
            
            // Artificial delay for visual feedback of sync
            setTimeout(() => setIsSyncing(false), 800);
        } catch (error) {
            console.error("Sync Error:", error);
            // Revert on error
            setSettings(prev => ({ ...prev, [field]: prevValue }));
            setIsSyncing(false);
            alert("⚠️ Connection Error: Failed to sync setting to cloud.");
        }
    };

    const isPositive = settings.price_change >= 0;
    const isConfigError = !import.meta.env.VITE_SUPABASE_URL || !import.meta.env.VITE_SUPABASE_URL.startsWith('https');

    return (
        <header className="border-b border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-card-dark/50 backdrop-blur-md sticky top-0 z-50">
            {isConfigError && (
                <div className="bg-red-500 text-white text-[10px] py-1 px-4 text-center font-bold tracking-wider animate-pulse">
                    ⚠️ CLOUD CONFIGURATION ERROR: CHECK VERCEL ENVIRONMENT VARIABLES
                </div>
            )}
            <div className="max-w-[1600px] mx-auto px-4 md:px-6 h-16 flex items-center justify-between">
                <div className="flex items-center gap-4 md:gap-8 overflow-hidden">
                    <div className="flex items-center gap-2 shrink-0">
                        <span className="material-symbols-outlined text-primary text-2xl md:text-3xl">toll</span>
                        <h1 className="text-lg md:text-xl font-extrabold tracking-tight text-primary truncate sm:block hidden">GoldSignalBot</h1>
                        <h1 className="text-lg font-extrabold tracking-tight text-primary block sm:hidden">GSB</h1>
                    </div>

                    {/* Bot Controller */}
                    <div className="hidden lg:flex items-center gap-4 border-l border-slate-800 pl-8 ml-2 lowercase">
                        <div className="flex flex-col">
                            <span className="text-[9px] text-slate-500 uppercase font-bold tracking-widest">Timeframe</span>
                            <select
                                value={settings.active_timeframe}
                                onChange={(e) => updateSetting('active_timeframe', e.target.value)}
                                className="bg-transparent text-xs font-bold text-slate-300 border-none p-0 focus:ring-0 cursor-pointer hover:text-primary transition-colors uppercase"
                            >
                                <option value="15m" className="bg-card-dark tracking-widest">15m (Fast)</option>
                                <option value="1h" className="bg-card-dark tracking-widest">1H (Standard)</option>
                                <option value="4h" className="bg-card-dark tracking-widest">4H (Swing)</option>
                                <option value="1d" className="bg-card-dark tracking-widest">1D (Trend)</option>
                            </select>
                        </div>

                        <div className="h-6 w-px bg-slate-800 mx-2"></div>

                        <div className="flex flex-col">
                            <span className="text-[9px] text-slate-500 uppercase font-bold tracking-widest">Strategy</span>
                            <select
                                value={settings.active_strategy}
                                onChange={(e) => updateSetting('active_strategy', e.target.value)}
                                className="bg-transparent text-xs font-bold text-slate-300 border-none p-0 focus:ring-0 cursor-pointer hover:text-primary transition-colors uppercase"
                            >
                                <option value="v1" className="bg-card-dark tracking-widest">V1 - EMA Cross</option>
                                <option value="v2" className="bg-card-dark tracking-widest">V2 - Breakout</option>
                                <option value="v3" className="bg-card-dark tracking-widest">V3 - Scalper</option>
                            </select>
                        </div>

                        {isSyncing && (
                            <div className="flex items-center gap-2 text-[9px] text-primary animate-pulse ml-4">
                                <span className="material-symbols-outlined text-sm">sync</span>
                                SYNCING BOT...
                            </div>
                        )}
                    </div>
                </div>

                <div className="flex items-center gap-6">
                    <div className="flex flex-col items-end">
                        <div className="flex items-center gap-2">
                            <span className={`text-sm font-bold ${isPositive ? 'text-success' : 'text-danger'} group relative cursor-help`}>
                                ${settings.current_price?.toLocaleString() || '0,000.00'}
                            </span>
                            <span className={`text-[10px] ${isPositive ? 'bg-success/20 text-success' : 'bg-danger/20 text-danger'} px-1.5 py-0.5 rounded`}>
                                {isPositive ? '+' : ''}{settings.price_change}%
                            </span>
                        </div>
                        <span className="text-[10px] text-slate-500 uppercase tracking-widest font-medium">LIVE • {settings.active_timeframe} SCAN</span>
                    </div>

                    <div className="flex items-center gap-3 border-l border-slate-200 dark:border-slate-800 pl-6">
                        <button className="relative p-2 text-slate-400 hover:text-white transition-colors">
                            <span className="material-symbols-outlined">notifications</span>
                        </button>
                        <div className="h-8 w-8 rounded-full bg-gradient-to-tr from-primary to-yellow-600 flex items-center justify-center text-background-dark font-bold text-xs ring-2 ring-primary/20">JD</div>
                    </div>
                </div>
            </div>
        </header>
    );
}

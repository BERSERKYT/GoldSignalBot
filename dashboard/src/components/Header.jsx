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
    const [showMobileMenu, setShowMobileMenu] = useState(false);

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

                    {/* Desktop Bot Controller */}
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
                                SYNCING...
                            </div>
                        )}
                    </div>
                </div>

                <div className="flex items-center gap-4 md:gap-6">
                    <div className="flex flex-col items-end">
                        <div className="flex items-center gap-2">
                            <span className={`text-sm font-bold ${isPositive ? 'text-success' : 'text-danger'} group relative cursor-help`}>
                                ${settings.current_price?.toLocaleString() || '0,000.00'}
                            </span>
                            <span className={`text-[10px] ${isPositive ? 'bg-success/20 text-success' : 'bg-danger/20 text-danger'} px-1.5 py-0.5 rounded sm:block hidden`}>
                                {isPositive ? '+' : ''}{settings.price_change}%
                            </span>
                        </div>
                        <span className="text-[10px] text-slate-500 uppercase tracking-widest font-medium">LIVE • {settings.active_timeframe}</span>
                    </div>

                    {/* AI Adaptation Status */}
                    <div className="hidden sm:flex flex-col items-center bg-slate-900/40 border border-slate-800 px-3 py-1.5 rounded-xl backdrop-blur-sm">
                        <div className="flex items-center gap-2">
                             <span className={`material-symbols-outlined text-sm ${settings.ai_status?.includes('Sharpening') ? 'animate-pulse text-primary' : 'text-slate-500'}`}>psychology</span>
                             <span className="text-[9px] font-black text-slate-300 uppercase tracking-tighter">AI ADAPTATION</span>
                        </div>
                        <div className="text-[10px] font-bold text-primary truncate max-w-[120px]">
                            {settings.ai_status || "Stable"}
                        </div>
                    </div>

                    <div className="flex items-center gap-2 md:gap-3 border-l border-slate-200 dark:border-slate-800 pl-4 md:pl-6">
                        {/* Mobile Settings Toggle */}
                        <button 
                            onClick={() => setShowMobileMenu(!showMobileMenu)}
                            className={`lg:hidden p-1.5 rounded-lg transition-colors ${showMobileMenu ? 'bg-primary text-background-dark' : 'text-slate-400 hover:bg-slate-800'}`}
                        >
                            <span className="material-symbols-outlined text-xl">settings</span>
                        </button>
                        
                        <button className="relative p-1.5 text-slate-400 hover:text-white transition-colors sm:block hidden">
                            <span className="material-symbols-outlined">notifications</span>
                            <div className="absolute top-1.5 right-1.5 w-2 h-2 bg-danger rounded-full border-2 border-background-dark"></div>
                        </button>
                        <div className="h-7 w-7 md:h-8 md:w-8 rounded-full bg-gradient-to-tr from-primary to-yellow-600 flex items-center justify-center text-background-dark font-bold text-[10px] md:text-xs ring-2 ring-primary/20 shrink-0">JD</div>
                    </div>
                </div>
            </div>

            {/* Mobile Settings Sub-menu */}
            {showMobileMenu && (
                <div className="lg:hidden bg-slate-900 border-b border-slate-800 p-4 flex flex-col gap-4 animate-in slide-in-from-top duration-300">
                    <div className="flex items-center justify-between">
                        <div className="flex flex-col flex-1">
                            <span className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-1">Select Timeframe</span>
                            <div className="flex gap-2">
                                {['15m', '1h', '4h', '1d'].map(tf => (
                                    <button 
                                        key={tf}
                                        onClick={() => updateSetting('active_timeframe', tf)}
                                        className={`flex-1 py-2 rounded text-[10px] font-bold uppercase transition-all ${settings.active_timeframe === tf ? 'bg-primary text-background-dark' : 'bg-slate-800 text-slate-400'}`}
                                    >
                                        {tf}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>

                    <div className="flex flex-col">
                        <span className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-1">Strategy Profile</span>
                        <div className="grid grid-cols-3 gap-2">
                            {['v1', 'v2', 'v3'].map(st => (
                                <button 
                                    key={st}
                                    onClick={() => updateSetting('active_strategy', st)}
                                    className={`py-2 rounded text-[10px] font-bold uppercase transition-all ${settings.active_strategy === st ? 'bg-primary text-background-dark' : 'bg-slate-800 text-slate-400'}`}
                                >
                                    {st.toUpperCase()}
                                </button>
                            ))}
                        </div>
                    </div>

                    {isSyncing && (
                        <div className="flex items-center justify-center gap-2 text-[10px] text-primary animate-pulse py-1">
                            <span className="material-symbols-outlined text-sm">sync</span>
                            APPLYING RULES TO CLOUD...
                        </div>
                    )}
                </div>
            )}
        </header>
    );
}

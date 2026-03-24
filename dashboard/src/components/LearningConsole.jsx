import React, { useState, useEffect } from 'react';
import { supabase } from '../lib/supabaseClient';

export default function LearningConsole() {
    const [aiInfo, setAiInfo] = useState({
        status: 'Stable',
        lesson: 'Bot is performing within expected parameters. Standard strategy logic applied.',
        updatedAt: null
    });

    useEffect(() => {
        const fetchAISettings = async () => {
            const { data, error } = await supabase
                .from('settings')
                .select('ai_status, ai_lessons, updated_at')
                .single();
            
            if (!error && data) {
                setAiInfo({
                    status: data.ai_status || 'Stable',
                    lesson: data.ai_lessons || 'Initial learning phase. Monitoring market patterns...',
                    updatedAt: data.updated_at
                });
            }
        };

        fetchAISettings();

        const subscription = supabase
            .channel('ai-learning-sync')
            .on('postgres_changes', { event: 'UPDATE', schema: 'public', table: 'settings' }, (payload) => {
                if (payload.new.ai_status || payload.new.ai_lessons) {
                    setAiInfo({
                        status: payload.new.ai_status || 'Stable',
                        lesson: payload.new.ai_lessons || 'Stable market conditions detected.',
                        updatedAt: payload.new.updated_at
                    });
                }
            })
            .subscribe();

        return () => supabase.removeChannel(subscription);
    }, []);

    const getStatusStyles = (status) => {
        switch (status) {
            case 'Defensive': return 'bg-primary/20 text-primary border-primary/30';
            case 'Adaptive': return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
            case 'Stable': return 'bg-success/20 text-success border-success/30';
            default: return 'bg-slate-800 text-slate-400 border-slate-700';
        }
    };

    return (
        <div className="bg-card-dark rounded-xl border border-slate-800 p-6 md:p-8 flex flex-col h-full relative overflow-hidden group hover:border-primary/40 transition-all duration-500">
            {/* Background Accent */}
            <div className="absolute -right-12 -top-12 w-48 h-48 bg-primary/5 rounded-full blur-3xl group-hover:bg-primary/10 transition-colors"></div>
            
            <div className="flex justify-between items-start mb-6 relative z-10">
                <div>
                    <h3 className="text-white font-bold text-base md:text-lg mb-1 flex items-center gap-2">
                        <span className="material-symbols-outlined text-primary">psychology</span>
                        AI Learning Console
                    </h3>
                    <p className="text-slate-500 text-[10px] md:text-xs uppercase font-bold tracking-widest">Bot Self-Optimization Engine</p>
                </div>
                <div className={`px-3 py-1 rounded-full border text-[10px] font-black uppercase tracking-widest ${getStatusStyles(aiInfo.status)}`}>
                    {aiInfo.status}
                </div>
            </div>

            <div className="flex-1 flex flex-col gap-6 relative z-10">
                <div className="bg-slate-900/60 rounded-2xl p-4 md:p-6 border border-slate-800/50">
                    <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mb-3">Latest Learned Lesson</p>
                    <p className="text-slate-200 text-sm md:text-base leading-relaxed font-medium">
                        "{aiInfo.lesson}"
                    </p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div className="p-3 md:p-4 rounded-xl bg-slate-900/40 border border-slate-800/50">
                        <p className="text-[9px] text-slate-500 font-bold uppercase mb-1">Knowledge State</p>
                        <div className="flex items-center gap-2">
                            <span className="text-xs text-white font-bold">Deep Patterns</span>
                            <div className="flex gap-0.5">
                                {[1, 2, 3, 4, 5].map(i => (
                                    <div key={i} className={`w-1 h-3 rounded-full ${i <= 4 ? 'bg-primary' : 'bg-slate-800'}`}></div>
                                ))}
                            </div>
                        </div>
                    </div>
                    <div className="p-3 md:p-4 rounded-xl bg-slate-900/40 border border-slate-800/50">
                        <p className="text-[9px] text-slate-500 font-bold uppercase mb-1">Update Frequency</p>
                        <span className="text-xs text-white font-bold">Every Scan (15m+)</span>
                    </div>
                </div>

                <div className="mt-auto pt-4 border-t border-slate-800/50 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <div className="w-1.5 h-1.5 bg-primary rounded-full animate-pulse"></div>
                        <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest shrink-0">AI is actively processing</span>
                    </div>
                    <span className="text-[9px] text-slate-600 font-medium">
                        Last Shift: {aiInfo.updatedAt ? new Date(aiInfo.updatedAt).toLocaleTimeString() : 'Waiting for next scan...'}
                    </span>
                </div>
            </div>
        </div>
    );
}

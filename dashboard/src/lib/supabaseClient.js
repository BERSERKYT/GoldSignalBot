import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

// Defensive check to prevent blank page on invalid config
if (!supabaseUrl || !supabaseUrl.startsWith('https')) {
    console.error("⚠️ SUPABASE CONFIG ERROR: VITE_SUPABASE_URL is missing or invalid. Dashboard will be in offline mode.");
}

export const supabase = createClient(
    supabaseUrl || 'https://placeholder.supabase.co', 
    supabaseAnonKey || 'placeholder'
)

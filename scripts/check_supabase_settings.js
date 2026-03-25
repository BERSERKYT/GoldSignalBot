const { createClient } = require('@supabase/supabase-js');
require('dotenv').config();

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_KEY;
const supabase = createClient(supabaseUrl, supabaseKey);

async function checkSettings() {
    console.log("Checking Supabase settings table...");
    const { data, error } = await supabase
        .from('settings')
        .select('*');
    
    if (error) {
        console.error("Error fetching settings:", error);
    } else {
        console.log("Settings data:", data);
    }
}

checkSettings();

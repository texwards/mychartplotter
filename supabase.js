import 'react-native-url-polyfill/auto'
import AsyncStorage from '@react-native-async-storage/async-storage'
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = 'YOUR_PROJECT_URL_HERE' // Paste from Dashboard
const supabaseAnonKey = 'YOUR_ANON_KEY_HERE' // Paste from Dashboard

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    storage: AsyncStorage, // Keeps the user logged in even if they close the app
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: false,
  },
})
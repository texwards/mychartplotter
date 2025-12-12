import { useState, useEffect } from 'react'
import { View, Text } from 'react-native'
import { supabase } from './supabase'
import Auth from './components/Auth'

export default function App() {
  const [session, setSession] = useState(null)

  useEffect(() => {
    // 1. Check active session on load
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
    })

    // 2. Listen for changes (Login, Logout, Auto-refresh)
    supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
    })
  }, [])

  return (
    <View style={{ flex: 1 }}>
      {session && session.user ? (
        // USER IS LOGGED IN
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
          <Text>Welcome, {session.user.email}!</Text>
          {/* Your Main App Tabs Go Here */}
        </View>
      ) : (
        // USER IS GUEST
        // You can either show the Auth screen OR the "Lazy" content
        <Auth /> 
      )}
    </View>
  )
}
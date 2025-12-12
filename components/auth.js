import React, { useState } from 'react'
import { Alert, StyleSheet, View, TextInput, Button, Text } from 'react-native'
import { supabase } from '../supabase' // Import the client we just made

export default function Auth() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [isLogin, setIsLogin] = useState(true) // Toggle between Login/Signup

  async function handleAuth() {
    setLoading(true)
    let error;
    
    if (isLogin) {
      // LOGIN LOGIC
      const response = await supabase.auth.signInWithPassword({
        email: email,
        password: password,
      })
      error = response.error
    } else {
      // SIGN UP LOGIC
      const response = await supabase.auth.signUp({
        email: email,
        password: password,
      })
      error = response.error
      if (!error) Alert.alert('Success', 'Check your email for the confirmation link!')
    }

    if (error) Alert.alert(error.message)
    setLoading(false)
  }

  return (
    <View style={styles.container}>
      <Text style={styles.header}>{isLogin ? 'Welcome Back' : 'Create Account'}</Text>
      
      <TextInput
        style={styles.input}
        placeholder="email@address.com"
        autoCapitalize="none"
        value={email}
        onChangeText={setEmail}
      />
      <TextInput
        style={styles.input}
        placeholder="Password"
        secureTextEntry={true}
        autoCapitalize="none"
        value={password}
        onChangeText={setPassword}
      />
      
      <View style={styles.btnContainer}>
        <Button 
          title={loading ? "Loading..." : (isLogin ? "Sign In" : "Sign Up")} 
          onPress={handleAuth} 
          disabled={loading}
        />
      </View>

      <View style={styles.toggleContainer}>
        <Text>
            {isLogin ? "Don't have an account? " : "Already have an account? "}
        </Text>
        <Button 
            title={isLogin ? "Sign Up" : "Log In"} 
            onPress={() => setIsLogin(!isLogin)} 
            type="clear" // Adjust based on your UI library
        />
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { padding: 20, justifyContent: 'center', flex: 1 },
  header: { fontSize: 24, fontWeight: 'bold', marginBottom: 20, textAlign: 'center' },
  input: { borderBottomWidth: 1, borderColor: '#ccc', padding: 10, marginBottom: 20 },
  btnContainer: { marginTop: 10 },
  toggleContainer: { marginTop: 20, flexDirection: 'row', justifyContent: 'center', alignItems: 'center' }
})
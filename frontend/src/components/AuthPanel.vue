<script setup>
import { reactive, ref } from 'vue'
import { api } from '../services/api'

const emit = defineEmits(['authenticated'])
const mode = ref('welcome')
const busy = ref(false)
const error = ref('')
const form = reactive({ username: '', display_name: '', email: '', password: '' })

async function submit() {
  busy.value = true
  error.value = ''
  try {
    const result = mode.value === 'register'
      ? await api.register({ ...form, email: form.email || null })
      : await api.login({ username: form.username, password: form.password })
    emit('authenticated', result)
  } catch (reason) {
    error.value = reason.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section v-if="mode === 'welcome'" class="welcome-card" aria-labelledby="welcome-title">
    <div class="welcome-art" data-node-id="6:37">
      <span class="orbit orbit-one" aria-hidden="true"></span>
      <span class="orbit orbit-two" aria-hidden="true"></span>
      <p>Make a little room for yourself.</p>
      <h1 id="welcome-title">Welcome to<br />Mindful Moments</h1>
    </div>
    <p class="welcome-copy">A private space to notice what happened, name how you feel, and choose what helps next.</p>
    <button class="primary-button wide" type="button" @click="mode = 'login'">Log in</button>
    <button class="secondary-button wide" type="button" @click="mode = 'register'">Create an account</button>
    <p class="privacy-note">Self-report only · No diagnoses · You stay in control</p>
  </section>

  <section v-else class="auth-card" aria-labelledby="auth-title">
    <button class="text-button back-button" type="button" @click="mode = 'welcome'">← Back</button>
    <p class="eyebrow">Mindful Moments</p>
    <h1 id="auth-title">{{ mode === 'register' ? 'Create your space' : 'Welcome back' }}</h1>
    <p>{{ mode === 'register' ? 'Start with only what we need for this local prototype.' : 'Pick up where you left off.' }}</p>
    <form @submit.prevent="submit">
      <label v-if="mode === 'register'">
        What should we call you?
        <input v-model.trim="form.display_name" autocomplete="name" maxlength="60" required />
      </label>
      <label>
        Username
        <input v-model.trim="form.username" autocomplete="username" minlength="3" maxlength="32" required />
      </label>
      <label v-if="mode === 'register'">
        Email <span class="optional">optional</span>
        <input v-model.trim="form.email" autocomplete="email" type="email" maxlength="120" />
      </label>
      <label>
        Password
        <input v-model="form.password" :autocomplete="mode === 'register' ? 'new-password' : 'current-password'" type="password" :minlength="mode === 'register' ? 8 : 1" required />
      </label>
      <p v-if="error" class="form-error" role="alert">{{ error }}</p>
      <button class="primary-button wide" :disabled="busy" type="submit">{{ busy ? 'One moment…' : mode === 'register' ? 'Continue' : 'Log in' }}</button>
    </form>
    <button class="text-button switch-button" type="button" @click="mode = mode === 'register' ? 'login' : 'register'">
      {{ mode === 'register' ? 'Already have an account? Log in' : 'New here? Create an account' }}
    </button>
  </section>
</template>


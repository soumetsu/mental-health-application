<script setup>
import { reactive, ref, watch } from 'vue'
import { api } from '../services/api'
import ProfileAvatar from './ProfileAvatar.vue'

const props = defineProps({
  token: { type: String, required: true },
  user: { type: Object, required: true },
})
const emit = defineEmits(['close', 'updated', 'open-profile', 'logout'])
const themes = [
  { key: 'sage', label: 'Soft sage', note: 'The original calm green palette.' },
  { key: 'lavender', label: 'Quiet lavender', note: 'Cool lilac with low visual intensity.' },
  { key: 'warm', label: 'Warm light', note: 'Cream and muted clay tones.' },
]
const form = reactive({
  email: '', theme: 'sage', text_size: 'default', reduce_motion: false,
  high_contrast: false, read_aloud: false, voice_input: false,
})
const busy = ref(false)
const error = ref('')
const saved = ref(false)
const speechInputAvailable = typeof window !== 'undefined'
  && Boolean(window.SpeechRecognition || window.webkitSpeechRecognition)

watch(() => props.user, (user) => {
  Object.assign(form, {
    email: user.email || '',
    theme: user.theme || 'sage',
    text_size: user.text_size || 'default',
    reduce_motion: Boolean(user.reduce_motion),
    high_contrast: Boolean(user.high_contrast),
    read_aloud: Boolean(user.read_aloud),
    voice_input: Boolean(user.voice_input),
  })
}, { immediate: true, deep: true })

async function save() {
  busy.value = true
  error.value = ''
  saved.value = false
  try {
    const updated = await api.updateSettings(props.token, {
      email: form.email.trim() || null,
      theme: form.theme,
      text_size: form.text_size,
      reduce_motion: form.reduce_motion,
      high_contrast: form.high_contrast,
      read_aloud: form.read_aloud,
      voice_input: form.voice_input,
    })
    emit('updated', updated)
    saved.value = true
  } catch (reason) {
    error.value = reason.message
  } finally {
    busy.value = false
  }
}

function memberSince(value) {
  return new Date(value).toLocaleDateString(undefined, { month: 'long', year: 'numeric' })
}
</script>

<template>
  <section class="account-page settings-page" aria-labelledby="settings-title">
    <button class="text-button back-button" type="button" @click="emit('close')">← Home</button>
    <div class="account-heading">
      <div><p class="eyebrow">Settings</p><h1 id="settings-title">Adjust the app around you.</h1><p>These choices are optional and saved to your local account.</p></div>
      <button class="settings-profile-link" type="button" @click="emit('open-profile')">
        <ProfileAvatar :avatar-key="user.avatar_key" :avatar-image="user.avatar_image" />
        <span><strong>{{ user.display_name }}</strong><small>Open profile</small></span>
      </button>
    </div>

    <form class="account-form" @submit.prevent="save">
      <section class="account-section" aria-labelledby="account-settings-title">
        <div class="section-heading-copy"><p class="eyebrow">Account</p><h2 id="account-settings-title">Account information</h2></div>
        <div class="form-grid">
          <label>Username<input :value="user.username" autocomplete="username" disabled /></label>
          <label>Email <span class="optional">optional</span><input v-model="form.email" autocomplete="email" maxlength="120" type="email" /></label>
        </div>
        <p class="settings-detail">Member since {{ memberSince(user.created_at) }} · Demo sessions expire whenever the backend restarts.</p>
      </section>

      <section class="account-section" aria-labelledby="settings-theme-title">
        <div class="section-heading-copy"><p class="eyebrow">Appearance</p><h2 id="settings-theme-title">Theme</h2><p>Choose a soft palette. Themes never change based on inferred mood or behavior.</p></div>
        <div class="theme-picker" role="radiogroup" aria-label="App theme">
          <label v-for="theme in themes" :key="theme.key" class="theme-choice" :class="`theme-${theme.key}`">
            <input v-model="form.theme" name="settings-theme" type="radio" :value="theme.key" />
            <span><i aria-hidden="true"></i><strong>{{ theme.label }}</strong><small>{{ theme.note }}</small></span>
          </label>
        </div>
      </section>

      <section class="account-section" aria-labelledby="accessibility-title">
        <div class="section-heading-copy"><p class="eyebrow">Accessibility</p><h2 id="accessibility-title">Reading and motion</h2><p>Choose only what feels helpful. You can change these at any time.</p></div>
        <fieldset class="setting-fieldset">
          <legend>Text size</legend>
          <div class="inline-options">
            <label><input v-model="form.text_size" type="radio" value="default" /><span>Standard</span></label>
            <label><input v-model="form.text_size" type="radio" value="large" /><span class="large-text-preview">Larger</span></label>
          </div>
        </fieldset>
        <div class="settings-switches">
          <label class="setting-switch"><span><strong>Reduce motion</strong><small>Minimize decorative movement and animated transitions.</small></span><input v-model="form.reduce_motion" type="checkbox" /></label>
          <label class="setting-switch"><span><strong>Higher contrast</strong><small>Strengthen text, borders, and button contrast.</small></span><input v-model="form.high_contrast" type="checkbox" /></label>
          <label class="setting-switch"><span><strong>Read chat replies automatically</strong><small>Speak new assistant replies. Every chat message also has its own play button.</small></span><input v-model="form.read_aloud" type="checkbox" /></label>
        </div>
      </section>

      <section class="account-section" aria-labelledby="voice-title">
        <div class="section-heading-copy"><p class="eyebrow">Voice</p><h2 id="voice-title">Conversation controls</h2><p>The app does not record or save raw audio. Your browser or operating system may process speech to produce a transcript.</p></div>
        <label class="setting-switch" :class="{ unavailable: !speechInputAvailable }">
          <span><strong>Enable voice conversation controls</strong><small>{{ speechInputAvailable ? 'Adds microphone and conversation controls to the support chat.' : 'Voice input is not available in this browser. Read aloud may still work.' }}</small></span>
          <input v-model="form.voice_input" :disabled="!speechInputAvailable" type="checkbox" />
        </label>
      </section>

      <section class="account-section technical-settings" aria-labelledby="privacy-title">
        <div class="section-heading-copy"><p class="eyebrow">Privacy and technical details</p><h2 id="privacy-title">About this prototype</h2></div>
        <dl>
          <div><dt>Journal storage</dt><dd>SQLite data on this computer</dd></div>
          <div><dt>Profile photo</dt><dd>Compressed and stored with the local account</dd></div>
          <div><dt>Voice audio</dt><dd>Not saved by this app; browser speech services may process it</dd></div>
          <div><dt>Authentication</dt><dd>Class demo only; not production-ready</dd></div>
        </dl>
        <button class="secondary-button" type="button" @click="emit('logout')">Log out of this session</button>
      </section>

      <p v-if="error" class="form-error" role="alert">{{ error }}</p>
      <p v-if="saved" class="form-success" role="status">Settings saved.</p>
      <div class="button-row end"><button class="primary-button" :disabled="busy" type="submit">{{ busy ? 'Saving…' : 'Save settings' }}</button></div>
    </form>
  </section>
</template>

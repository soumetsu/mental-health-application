<script setup>
import { reactive, ref, watch } from 'vue'
import { api } from '../services/api'
import ProfileAvatar from './ProfileAvatar.vue'

const props = defineProps({
  token: { type: String, required: true },
  user: { type: Object, required: true },
})
const emit = defineEmits(['close', 'updated', 'open-settings'])

const avatarChoices = [
  { key: 'leaf', label: 'Leaf' },
  { key: 'moon', label: 'Moon' },
  { key: 'tea', label: 'Tea cup' },
  { key: 'fox', label: 'Fox' },
]
const themes = [
  { key: 'sage', label: 'Soft sage' },
  { key: 'lavender', label: 'Quiet lavender' },
  { key: 'warm', label: 'Warm light' },
]
const form = reactive({
  display_name: '', email: '', bio: '', avatar_key: 'leaf', avatar_image: '', theme: 'sage',
})
const busy = ref(false)
const photoBusy = ref(false)
const error = ref('')
const saved = ref(false)

watch(() => props.user, (user) => {
  Object.assign(form, {
    display_name: user.display_name,
    email: user.email || '',
    bio: user.bio || '',
    avatar_key: user.avatar_key || 'leaf',
    avatar_image: user.avatar_image || '',
    theme: user.theme || 'sage',
  })
}, { immediate: true, deep: true })

function chooseAvatar(key) {
  form.avatar_key = key
  form.avatar_image = ''
}

function loadImage(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const image = new Image()
    image.onload = () => resolve({ image, url })
    image.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('That image could not be opened.'))
    }
    image.src = url
  })
}

async function selectPhoto(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
    error.value = 'Choose a PNG, JPEG, or WebP image.'
    return
  }
  if (file.size > 5 * 1024 * 1024) {
    error.value = 'Choose an image smaller than 5 MB.'
    return
  }
  photoBusy.value = true
  error.value = ''
  try {
    const { image, url } = await loadImage(file)
    const canvas = document.createElement('canvas')
    const size = 320
    canvas.width = size
    canvas.height = size
    const scale = Math.max(size / image.naturalWidth, size / image.naturalHeight)
    const width = image.naturalWidth * scale
    const height = image.naturalHeight * scale
    canvas.getContext('2d').drawImage(image, (size - width) / 2, (size - height) / 2, width, height)
    URL.revokeObjectURL(url)
    form.avatar_image = canvas.toDataURL('image/jpeg', 0.82)
  } catch (reason) {
    error.value = reason.message
  } finally {
    photoBusy.value = false
  }
}

async function save() {
  busy.value = true
  error.value = ''
  saved.value = false
  try {
    const updated = await api.updateProfile(props.token, {
      display_name: form.display_name.trim(),
      email: form.email.trim() || null,
      bio: form.bio.trim(),
      avatar_key: form.avatar_key,
      avatar_image: form.avatar_image || null,
      theme: form.theme,
    })
    emit('updated', updated)
    saved.value = true
  } catch (reason) {
    error.value = reason.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section class="account-page profile-page" aria-labelledby="profile-title">
    <button class="text-button back-button" type="button" @click="emit('close')">← Home</button>
    <form class="account-form" @submit.prevent="save">
      <section class="account-section profile-primary-card" aria-labelledby="profile-title">
        <div class="profile-primary-header">
          <ProfileAvatar class="profile-avatar-large" :avatar-key="form.avatar_key" :avatar-image="form.avatar_image" />
          <div>
            <p class="eyebrow">Your profile</p>
            <h1 id="profile-title">{{ form.display_name || user.display_name }}</h1>
            <p>@{{ user.username }}</p>
          </div>
        </div>
        <div class="profile-primary-grid">
          <div class="profile-photo-tools">
            <label class="secondary-button upload-button small">
              {{ photoBusy ? 'Preparing photo…' : 'Upload a photo' }}
              <input accept="image/jpeg,image/png,image/webp" :disabled="photoBusy" type="file" @change="selectPhoto" />
            </label>
            <button v-if="form.avatar_image" class="text-button" type="button" @click="chooseAvatar(form.avatar_key)">Remove uploaded photo</button>
            <details class="avatar-options">
              <summary>Choose a sample icon</summary>
              <div class="avatar-picker compact-avatar-picker" role="group" aria-label="Sample profile pictures">
                <button
                  v-for="choice in avatarChoices"
                  :key="choice.key"
                  class="avatar-choice"
                  :class="{ selected: !form.avatar_image && form.avatar_key === choice.key }"
                  :aria-pressed="!form.avatar_image && form.avatar_key === choice.key"
                  type="button"
                  @click="chooseAvatar(choice.key)"
                >
                  <ProfileAvatar :avatar-key="choice.key" />
                  <span>{{ choice.label }}</span>
                </button>
              </div>
            </details>
            <p>Uploaded photos are cropped to a square and saved with this local account.</p>
          </div>
          <div class="profile-detail-fields">
            <div class="form-grid">
              <label>Display name<input v-model="form.display_name" autocomplete="name" maxlength="60" required /></label>
              <label>Username<input :value="user.username" autocomplete="username" disabled /><span class="field-help">Usernames cannot be changed in this prototype.</span></label>
            </div>
            <label>Email <span class="optional">optional</span><input v-model="form.email" autocomplete="email" maxlength="120" type="email" /></label>
            <label>About me <span class="optional">optional</span><textarea v-model="form.bio" maxlength="280" rows="3" placeholder="A few words about what helps you feel grounded."></textarea><span class="field-help">{{ form.bio.length }}/280</span></label>
          </div>
        </div>
      </section>

      <section class="account-section" aria-labelledby="profile-theme-title">
        <div class="section-heading-copy"><p class="eyebrow">Appearance</p><h2 id="profile-theme-title">Choose a theme</h2><p>The theme applies throughout the app and can also be changed in Settings.</p></div>
        <div class="theme-picker" role="radiogroup" aria-label="App theme">
          <label v-for="theme in themes" :key="theme.key" class="theme-choice" :class="`theme-${theme.key}`">
            <input v-model="form.theme" name="profile-theme" type="radio" :value="theme.key" />
            <span><i aria-hidden="true"></i><strong>{{ theme.label }}</strong></span>
          </label>
        </div>
      </section>

      <aside class="accessibility-link-card">
        <div><strong>Need reading, motion, contrast, or voice support?</strong><p>Accessibility options and voice controls are grouped in Settings.</p></div>
        <button class="secondary-button" type="button" @click="emit('open-settings')">Open accessibility settings</button>
      </aside>

      <p v-if="error" class="form-error" role="alert">{{ error }}</p>
      <p v-if="saved" class="form-success" role="status">Your profile has been saved.</p>
      <div class="button-row end"><button class="primary-button" :disabled="busy || photoBusy" type="submit">{{ busy ? 'Saving…' : 'Save profile' }}</button></div>
    </form>
  </section>
</template>

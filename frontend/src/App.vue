<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import AuthPanel from './components/AuthPanel.vue'
import CheckInFlow from './components/CheckInFlow.vue'
import ChatbotWidget from './components/ChatbotWidget.vue'
import CrisisSupport from './components/CrisisSupport.vue'
import EventCalendar from './components/EventCalendar.vue'
import ExercisePanel from './components/ExercisePanel.vue'
import ProfileAvatar from './components/ProfileAvatar.vue'
import ProfilePanel from './components/ProfilePanel.vue'
import QuestionnairePanel from './components/QuestionnairePanel.vue'
import ReadPageButton from './components/ReadPageButton.vue'
import SettingsPanel from './components/SettingsPanel.vue'
import { api } from './services/api'

const token = ref(localStorage.getItem('mindful_token') || '')
const user = ref(null)
const dashboard = ref(null)
const events = ref([])
const exercises = ref([])
const screen = ref('welcome')
const loading = ref(Boolean(token.value))
const busy = ref(false)
const error = ref('')
const showEventForm = ref(false)
const profileMenuOpen = ref(false)
const eventForm = reactive({
  title: '', details: '', valence: 'positive', intensity: 3,
  happened_on: new Date().toISOString().slice(0, 10),
})
const headerAvatarSrc = computed(() => {
  if (user.value?.avatar_image) return user.value.avatar_image
  const key = ['leaf', 'moon', 'tea', 'fox'].includes(user.value?.avatar_key) ? user.value.avatar_key : 'leaf'
  return `/avatars/${key}.png`
})

watch(user, (currentUser) => {
  const root = document.documentElement
  root.dataset.theme = currentUser?.theme || 'sage'
  root.dataset.textSize = currentUser?.text_size || 'default'
  root.dataset.reduceMotion = String(Boolean(currentUser?.reduce_motion))
  root.dataset.highContrast = String(Boolean(currentUser?.high_contrast))
}, { immediate: true, deep: true })

onMounted(async () => {
  if (!token.value) return
  try {
    user.value = await api.me(token.value)
    if (user.value.has_questionnaire) await loadDashboard()
    else screen.value = 'onboarding'
  } catch {
    clearSession()
  } finally {
    loading.value = false
  }
})

function clearSession() {
  localStorage.removeItem('mindful_token')
  token.value = ''
  user.value = null
  dashboard.value = null
  screen.value = 'welcome'
}

async function handleAuthenticated(session) {
  token.value = session.token
  user.value = session.user
  localStorage.setItem('mindful_token', session.token)
  if (session.user.has_questionnaire) await loadDashboard()
  else screen.value = 'onboarding'
}

async function saveQuestionnaire(payload) {
  busy.value = true
  error.value = ''
  try {
    await api.saveQuestionnaire(token.value, payload)
    user.value.has_questionnaire = true
    await loadDashboard()
  } catch (reason) {
    error.value = reason.message
  } finally {
    busy.value = false
  }
}

async function loadDashboard() {
  loading.value = true
  error.value = ''
  try {
    const [dashboardData, eventData, exerciseData] = await Promise.all([
      api.dashboard(token.value), api.events(token.value), api.exercises(),
    ])
    dashboard.value = dashboardData
    events.value = eventData
    exercises.value = exerciseData
    screen.value = 'dashboard'
  } catch (reason) {
    if (reason.status === 401) clearSession()
    else error.value = reason.message
  } finally {
    loading.value = false
  }
}

async function logOut() {
  profileMenuOpen.value = false
  try { await api.logout(token.value) } catch { /* Clear the local session regardless. */ }
  clearSession()
}

async function saveEvent() {
  busy.value = true
  error.value = ''
  try {
    const saved = await api.createEvent(token.value, { ...eventForm, intensity: Number(eventForm.intensity) })
    events.value.unshift(saved)
    showEventForm.value = false
    eventForm.title = ''
    eventForm.details = ''
    await refreshDashboard()
  } catch (reason) {
    error.value = reason.message
  } finally {
    busy.value = false
  }
}

async function deleteEvent(id) {
  try {
    await api.deleteEvent(token.value, id)
    events.value = events.value.filter((item) => item.id !== id)
    await refreshDashboard()
  } catch (reason) {
    error.value = reason.message
  }
}

async function refreshDashboard() {
  dashboard.value = await api.dashboard(token.value)
}

function finishCheckIn() {
  loadDashboard()
}

function updateUser(updated) {
  user.value = updated
  if (dashboard.value) dashboard.value.display_name = updated.display_name
}

function openScreen(destination) {
  profileMenuOpen.value = false
  screen.value = destination
}
</script>

<template>
  <CrisisSupport />
  <div class="app-shell">
    <header v-if="user" class="app-header">
      <button class="brand-button" type="button" @click="openScreen('dashboard')" aria-label="Mindful Moments home">
        <span aria-hidden="true">✦</span> Mindful Moments
      </button>
      <div class="header-actions">
        <div class="profile-menu" @keydown.esc="profileMenuOpen = false">
          <button
            class="profile-menu-button"
            type="button"
            :aria-expanded="profileMenuOpen"
            aria-controls="profile-dropdown"
            :aria-label="`Open account menu for ${user.display_name}`"
            @click="profileMenuOpen = !profileMenuOpen"
          >
            <img class="header-avatar-image" :src="headerAvatarSrc" alt="" />
          </button>
          <button v-if="profileMenuOpen" class="profile-menu-backdrop" type="button" tabindex="-1" aria-hidden="true" @click="profileMenuOpen = false"></button>
          <section v-if="profileMenuOpen" id="profile-dropdown" class="profile-dropdown" aria-label="Account menu">
            <button class="profile-dropdown-summary" type="button" @click="openScreen('profile')">
              <ProfileAvatar :avatar-key="user.avatar_key" :avatar-image="user.avatar_image" />
              <span><strong>{{ user.display_name }}</strong><small>@{{ user.username }}</small><em>View and edit profile</em></span>
            </button>
            <div class="profile-dropdown-actions">
              <button class="text-button" type="button" @click="openScreen('settings')"><span aria-hidden="true">⚙</span>Settings</button>
              <ReadPageButton />
              <button class="text-button danger" type="button" @click="logOut"><span aria-hidden="true">↪</span>Log out</button>
            </div>
          </section>
        </div>
      </div>
    </header>

    <main :class="{ 'guest-main': !user }">
      <div v-if="loading" class="loading-card" role="status"><span class="spinner" aria-hidden="true"></span>Preparing your space…</div>
      <AuthPanel v-else-if="!user" @authenticated="handleAuthenticated" />
      <QuestionnairePanel v-else-if="screen === 'onboarding'" :busy="busy" :error="error" @save="saveQuestionnaire" />
      <CheckInFlow v-else-if="screen === 'checkin'" :token="token" @cancel="screen = 'dashboard'" @complete="finishCheckIn" />
      <ExercisePanel v-else-if="screen === 'exercises'" :token="token" :exercises="exercises" :recommended-id="dashboard?.recommended_exercise_id" @close="screen = 'dashboard'" />
      <ProfilePanel
        v-else-if="screen === 'profile'"
        :token="token"
        :user="user"
        @close="screen = 'dashboard'"
        @open-settings="screen = 'settings'"
        @updated="updateUser"
      />
      <SettingsPanel
        v-else-if="screen === 'settings'"
        :token="token"
        :user="user"
        @close="screen = 'dashboard'"
        @logout="logOut"
        @open-profile="screen = 'profile'"
        @updated="updateUser"
      />

      <div v-else-if="dashboard" class="dashboard-page" :data-support-state="dashboard.support_state">
        <section class="dashboard-banner" data-node-id="15:2">
          <div>
            <p class="eyebrow">{{ new Date().toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' }) }}</p>
            <h1>Welcome back, {{ dashboard.display_name }}.</h1>
            <p>{{ dashboard.message }}</p>
          </div>
          <span class="banner-mark" aria-hidden="true">✦</span>
        </section>

        <p v-if="error" class="form-error dashboard-error" role="alert">{{ error }}</p>

        <div class="dashboard-grid">
          <section class="checkin-card">
            <p class="eyebrow">Today’s check-in</p>
            <h2>{{ dashboard.today_check_in_complete ? 'You checked in today.' : 'How are you, really?' }}</h2>
            <p>{{ dashboard.today_check_in_complete ? 'Another check-in is always available, but there is no need to repeat it.' : 'Two small questions. Most days take less than a minute.' }}</p>
            <button class="primary-button" type="button" @click="screen = 'checkin'">{{ dashboard.today_check_in_complete ? 'Check in again' : 'Begin' }} →</button>
          </section>

          <section class="impact-card">
            <span class="impact-number">{{ dashboard.today_event_count }}</span>
            <div><p class="eyebrow">Impactful events today</p><h2>{{ dashboard.today_event_count ? 'You noticed what happened.' : 'Nothing logged yet.' }}</h2></div>
            <button class="secondary-button small" type="button" @click="showEventForm = true">Add event</button>
          </section>

          <EventCalendar class="calendar-area" :events="events" @add="showEventForm = true" @delete="deleteEvent" />

          <aside class="suggestion-card">
            <span aria-hidden="true" class="suggestion-icon">◌</span>
            <h2>A short reset is here if you want it.</h2>
            <p>{{ dashboard.affirmation }}</p>
            <button class="secondary-button" type="button" @click="screen = 'exercises'">Choose an exercise</button>
          </aside>
        </div>
      </div>
    </main>

    <nav v-if="user && dashboard && ['dashboard', 'checkin', 'exercises'].includes(screen)" class="bottom-nav" aria-label="Primary navigation">
      <button :class="{ active: screen === 'dashboard' }" type="button" @click="screen = 'dashboard'"><span aria-hidden="true">⌂</span>Home</button>
      <button :class="{ active: screen === 'checkin' }" type="button" @click="screen = 'checkin'"><span aria-hidden="true">✓</span>Check-in</button>
      <button :class="{ active: screen === 'exercises' }" type="button" @click="screen = 'exercises'"><span aria-hidden="true">◌</span>Exercises</button>
    </nav>
    <ChatbotWidget
      v-if="user && dashboard && screen !== 'onboarding'"
      :token="token"
      :read-aloud="user.read_aloud"
      :voice-input="user.voice_input"
      @navigate="screen = $event"
    />
  </div>

  <div v-if="showEventForm" class="modal-backdrop" @click.self="showEventForm = false">
    <section class="modal-card" role="dialog" aria-modal="true" aria-labelledby="event-title">
      <button class="icon-button close-modal" type="button" aria-label="Close" @click="showEventForm = false">×</button>
      <p class="eyebrow">Event logger</p>
      <h1 id="event-title">What happened?</h1>
      <p>Record only what feels useful. Short is completely fine.</p>
      <form @submit.prevent="saveEvent">
        <label>Event name<input v-model.trim="eventForm.title" maxlength="100" required placeholder="e.g. Helpful conversation" /></label>
        <fieldset class="choice-fieldset"><legend>How did it land?</legend><div class="segmented-control">
          <label><input v-model="eventForm.valence" type="radio" value="positive" /><span>Positive</span></label>
          <label><input v-model="eventForm.valence" type="radio" value="neutral" /><span>Neutral</span></label>
          <label><input v-model="eventForm.valence" type="radio" value="negative" /><span>Difficult</span></label>
        </div></fieldset>
        <label>Date<input v-model="eventForm.happened_on" type="date" required /></label>
        <label class="range-label">How impactful was it? <strong>{{ eventForm.intensity }}/5</strong><input v-model.number="eventForm.intensity" type="range" min="1" max="5" /></label>
        <label>Anything else? <span class="optional">optional</span><textarea v-model.trim="eventForm.details" maxlength="800" rows="3"></textarea></label>
        <p v-if="error" class="form-error" role="alert">{{ error }}</p>
        <div class="button-row"><button class="secondary-button" type="button" @click="showEventForm = false">Cancel</button><button class="primary-button" :disabled="busy" type="submit">{{ busy ? 'Saving…' : 'Save event' }}</button></div>
      </form>
    </section>
  </div>
</template>


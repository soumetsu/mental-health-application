<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { api } from '../services/api'

const props = defineProps({
  token: { type: String, required: true },
  exercises: { type: Array, default: () => [] },
  recommendedId: { type: String, default: '' },
})
const emit = defineEmits(['close'])

const activeId = ref('')
const activeHistoryId = ref('')
const groundingIndex = ref(0)
const breathingPhaseIndex = ref(0)
const breathingRound = ref(0)
const completedName = ref('')
const history = ref([])
const historyBusy = ref(false)
const actionBusy = ref(false)
const error = ref('')
const editingId = ref('')
const reflectionDrafts = reactive({})
let phaseTimer

const breathingPhases = [
  { label: 'Breathe in gently', className: 'inhale' },
  { label: 'Pause if comfortable', className: 'hold' },
  { label: 'Breathe out gently', className: 'exhale' },
  { label: 'Rest', className: 'rest' },
]
const ordered = computed(() => [...props.exercises].sort(
  (a, b) => Number(b.id === props.recommendedId) - Number(a.id === props.recommendedId),
))
const active = computed(() => props.exercises.find((item) => item.id === activeId.value))
const currentBreathingPhase = computed(() => breathingPhases[breathingPhaseIndex.value])
const groundingWords = ['five', 'four', 'three', 'two', 'one']

onMounted(loadHistory)

async function loadHistory() {
  historyBusy.value = true
  try {
    history.value = await api.exerciseHistory(props.token)
  } catch (reason) {
    error.value = reason.message
  } finally {
    historyBusy.value = false
  }
}

async function start(item) {
  actionBusy.value = true
  error.value = ''
  completedName.value = ''
  try {
    const entry = await api.startExercise(props.token, item.id)
    activeHistoryId.value = entry.id
    activeId.value = item.id
    groundingIndex.value = 0
    breathingPhaseIndex.value = 0
    breathingRound.value = 0
    if (item.id === 'box-breathing') scheduleNextBreathingPhase()
  } catch (reason) {
    error.value = reason.message
  } finally {
    actionBusy.value = false
  }
}

function scheduleNextBreathingPhase() {
  clearTimeout(phaseTimer)
  phaseTimer = setTimeout(async () => {
    if (breathingPhaseIndex.value === breathingPhases.length - 1) {
      if (breathingRound.value === 3) {
        await finish('completed')
        return
      }
      breathingRound.value += 1
      breathingPhaseIndex.value = 0
    } else {
      breathingPhaseIndex.value += 1
    }
    scheduleNextBreathingPhase()
  }, 4000)
}

async function nextGroundingStep() {
  if (groundingIndex.value < active.value.steps.length - 1) {
    groundingIndex.value += 1
    return
  }
  await finish('completed')
}

async function finish(status) {
  clearTimeout(phaseTimer)
  if (!activeHistoryId.value) return
  actionBusy.value = true
  const name = active.value?.title || 'Exercise'
  const historyId = activeHistoryId.value
  activeHistoryId.value = ''
  try {
    await api.updateExerciseHistory(props.token, historyId, { status })
    if (status === 'completed') completedName.value = name
    activeId.value = ''
    await loadHistory()
  } catch (reason) {
    activeHistoryId.value = historyId
    error.value = reason.message
  } finally {
    actionBusy.value = false
  }
}

async function leavePanel() {
  if (activeHistoryId.value) await finish('stopped')
  emit('close')
}

function beginReflection(entry) {
  editingId.value = entry.id
  reflectionDrafts[entry.id] = entry.reflection
}

async function saveReflection(entry) {
  actionBusy.value = true
  error.value = ''
  try {
    const updated = await api.updateExerciseHistory(props.token, entry.id, {
      reflection: reflectionDrafts[entry.id] ?? '',
    })
    history.value = history.value.map((item) => item.id === entry.id ? updated : item)
    editingId.value = ''
  } catch (reason) {
    error.value = reason.message
  } finally {
    actionBusy.value = false
  }
}

async function removeHistory(entry) {
  if (!window.confirm(`Delete the ${entry.exercise_title} history entry?`)) return
  try {
    await api.deleteExerciseHistory(props.token, entry.id)
    history.value = history.value.filter((item) => item.id !== entry.id)
  } catch (reason) {
    error.value = reason.message
  }
}

function formatDate(value) {
  return new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

onBeforeUnmount(() => {
  clearTimeout(phaseTimer)
  if (activeHistoryId.value) {
    api.updateExerciseHistory(props.token, activeHistoryId.value, { status: 'stopped' }).catch(() => {})
    activeHistoryId.value = ''
  }
})
</script>

<template>
  <section class="flow-card exercises" aria-labelledby="exercise-title">
    <button class="text-button back-button" type="button" @click="leavePanel">← Home</button>

    <div v-if="active" class="active-exercise" aria-live="polite">
      <template v-if="active.id === 'grounding-54321'">
        <p class="eyebrow">5-4-3-2-1 grounding</p>
        <div class="grounding-number" aria-hidden="true">{{ 5 - groundingIndex }}</div>
        <h1 id="exercise-title">{{ active.steps[groundingIndex] }}</h1>
        <p>Take your time and notice ordinary details around you. You can name them silently or out loud.</p>
        <button class="primary-button" :disabled="actionBusy" type="button" @click="nextGroundingStep">
          {{ groundingIndex === active.steps.length - 1 ? 'Finish exercise' : `I noticed ${groundingWords[groundingIndex]}` }}
        </button>
      </template>

      <template v-else>
        <p class="eyebrow">Four-count breathing</p>
        <div class="breathing-orb" :class="currentBreathingPhase.className" aria-hidden="true"></div>
        <h1 id="exercise-title">{{ currentBreathingPhase.label }}</h1>
        <p>Let the rhythm guide you without forcing the breath. Keep both feet supported if that feels comfortable.</p>
        <div class="breath-progress" aria-label="Breathing cycle progress">
          <i v-for="round in 4" :key="round" :class="{ complete: round - 1 < breathingRound }"></i>
        </div>
      </template>

      <p class="exercise-safety">Stop and breathe normally if you feel dizzy, light-headed, or uncomfortable.</p>
      <button class="secondary-button" :disabled="actionBusy" type="button" @click="finish('stopped')">Stop</button>
    </div>

    <template v-else>
      <p class="eyebrow">Optional exercises</p>
      <h1 id="exercise-title">Choose what sounds manageable.</h1>
      <p>Nothing starts on its own. Stop whenever you want. The app keeps a private history, but never displays how long you took.</p>

      <div v-if="completedName" class="exercise-complete" role="status">
        <span aria-hidden="true">✓</span>
        <div><strong>{{ completedName }} saved</strong><p>You can add a private reflection in your history below.</p></div>
      </div>

      <p v-if="error" class="form-error" role="alert">{{ error }}</p>
      <div class="exercise-grid">
        <article v-for="item in ordered" :key="item.id" class="exercise-card" :class="{ recommended: item.id === recommendedId }">
          <span v-if="item.id === recommendedId" class="recommendation-label">Suggested for today</span>
          <h2>{{ item.title }}</h2>
          <p>{{ item.summary }}</p>
          <button class="primary-button small" :disabled="actionBusy" type="button" @click="start(item)">Start</button>
        </article>
      </div>

      <section class="exercise-history" aria-labelledby="history-title">
        <div class="section-heading">
          <div><p class="eyebrow">Private activity log</p><h2 id="history-title">Exercise history</h2></div>
          <button class="text-button" type="button" @click="loadHistory">Refresh</button>
        </div>
        <p v-if="historyBusy" class="empty-state" role="status">Loading history…</p>
        <p v-else-if="history.length === 0" class="empty-state">No exercises recorded yet.</p>
        <article v-for="entry in history" v-else :key="entry.id" class="history-item">
          <div class="history-main">
            <span class="history-status" :class="entry.status">{{ entry.status.replace('_', ' ') }}</span>
            <strong>{{ entry.exercise_title }}</strong>
            <span>{{ formatDate(entry.started_at) }}</span>
          </div>
          <form v-if="editingId === entry.id" class="reflection-editor" @submit.prevent="saveReflection(entry)">
            <label>Private reflection<textarea v-model="reflectionDrafts[entry.id]" maxlength="400" rows="3" placeholder="What did you notice?"></textarea></label>
            <div class="button-row"><button class="text-button" type="button" @click="editingId = ''">Cancel</button><button class="primary-button small" :disabled="actionBusy" type="submit">Save</button></div>
          </form>
          <p v-else-if="entry.reflection" class="history-reflection">“{{ entry.reflection }}”</p>
          <div v-if="editingId !== entry.id" class="history-actions">
            <button class="text-button" type="button" @click="beginReflection(entry)">{{ entry.reflection ? 'Edit reflection' : 'Add reflection' }}</button>
            <button class="text-button danger" type="button" @click="removeHistory(entry)">Delete</button>
          </div>
        </article>
      </section>
    </template>
  </section>
</template>

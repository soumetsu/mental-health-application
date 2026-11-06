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
const breathingMode = ref('')
const breathingPhaseIndex = ref(0)
const breathingRound = ref(0)
const breathingPaused = ref(false)
const breathingHolding = ref(false)
const completedName = ref('')
const history = ref([])
const historyBusy = ref(false)
const actionBusy = ref(false)
const error = ref('')
const editingId = ref('')
const reflectionDrafts = reactive({})
let phaseTimer
let phaseStartedAt = 0
let phaseRemainingMs = 4000

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
const breathingProgress = computed(() => {
  if (breathingMode.value === 'interactive') {
    return ((breathingRound.value + (breathingHolding.value ? 0.5 : 0)) / 4) * 100
  }
  if (breathingMode.value !== 'timer') return 0
  return (
    (breathingRound.value * breathingPhases.length + breathingPhaseIndex.value)
    / (breathingPhases.length * 4)
  ) * 100
})
const interactiveBreathingLabel = computed(() => (
  breathingHolding.value
    ? 'Breathe in gently'
    : breathingRound.value === 0 ? 'Breathe in when ready' : 'Breathe out gently'
))
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
    breathingMode.value = ''
    breathingPhaseIndex.value = 0
    breathingRound.value = 0
    breathingPaused.value = false
    breathingHolding.value = false
    phaseRemainingMs = 4000
  } catch (reason) {
    error.value = reason.message
  } finally {
    actionBusy.value = false
  }
}

function beginBreathing(mode) {
  clearTimeout(phaseTimer)
  breathingMode.value = mode
  breathingPhaseIndex.value = 0
  breathingRound.value = 0
  breathingPaused.value = false
  breathingHolding.value = false
  phaseRemainingMs = 4000
  if (mode === 'timer') scheduleNextBreathingPhase()
}

function chooseBreathingMethod() {
  clearTimeout(phaseTimer)
  breathingMode.value = ''
  breathingPhaseIndex.value = 0
  breathingRound.value = 0
  breathingPaused.value = false
  breathingHolding.value = false
  phaseRemainingMs = 4000
}

function startInteractiveInhale(event) {
  if (breathingMode.value !== 'interactive' || breathingHolding.value || actionBusy.value) return
  if (event?.pointerId !== undefined) event.currentTarget?.setPointerCapture?.(event.pointerId)
  breathingHolding.value = true
}

async function completeInteractiveBreath() {
  if (breathingMode.value !== 'interactive' || !breathingHolding.value || actionBusy.value) return
  breathingHolding.value = false
  if (breathingRound.value === 3) {
    await finish('completed')
    return
  }
  breathingRound.value += 1
}

function cancelInteractiveInhale() {
  breathingHolding.value = false
}

function scheduleNextBreathingPhase() {
  clearTimeout(phaseTimer)
  if (breathingPaused.value) return
  phaseStartedAt = Date.now()
  phaseTimer = setTimeout(async () => {
    phaseRemainingMs = 4000
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
  }, phaseRemainingMs)
}

function toggleBreathingPause() {
  if (breathingPaused.value) {
    breathingPaused.value = false
    scheduleNextBreathingPhase()
    return
  }
  phaseRemainingMs = Math.max(0, phaseRemainingMs - (Date.now() - phaseStartedAt))
  breathingPaused.value = true
  clearTimeout(phaseTimer)
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
  breathingPaused.value = false
  breathingHolding.value = false
  breathingMode.value = ''
  phaseRemainingMs = 4000
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
        <template v-if="!breathingMode">
          <h1 id="exercise-title">Choose how you want to breathe.</h1>
          <p>Try the hold button at your own pace, or use the four-count timer for a guided rhythm.</p>
          <div class="breathing-tutorial" aria-label="Hold button tutorial">
            <div><span aria-hidden="true">1</span><p><strong>Press and hold</strong> while you breathe in.</p></div>
            <div><span aria-hidden="true">2</span><p><strong>Let go</strong> while you breathe out.</p></div>
            <div><span aria-hidden="true">3</span><p><strong>Repeat four times.</strong> Take as long as feels comfortable.</p></div>
          </div>
          <div class="breathing-method-actions">
            <div class="hold-method-preview-wrap">
              <button
                class="primary-button"
                aria-describedby="hold-method-preview"
                type="button"
                @click="beginBreathing('interactive')"
              >Try hold-to-breathe</button>
              <div id="hold-method-preview" class="hold-method-preview" role="tooltip">
                <div class="hold-preview-animation" aria-hidden="true">
                  <div class="mouse-hold-demo">
                    <div class="mouse-shape"><span></span></div>
                    <span class="press-arrow">↓</span>
                    <span class="demo-hold-surface">Hold</span>
                  </div>
                  <div class="breathing-avatar-demo">
                    <span class="breath-arrows inhale-arrows">→ <b>←</b></span>
                    <span class="breath-arrows exhale-arrows">← <b>→</b></span>
                    <span class="avatar-head"></span>
                    <span class="avatar-body"></span>
                  </div>
                </div>
                <strong>Hold to breathe in. Release to breathe out.</strong>
              </div>
            </div>
            <button class="secondary-button" type="button" @click="beginBreathing('timer')">Use four-count timer</button>
          </div>
        </template>

        <template v-else-if="breathingMode === 'interactive'">
          <button
            class="breathing-hold-button"
            :class="{ holding: breathingHolding }"
            :aria-pressed="breathingHolding"
            :disabled="actionBusy"
            type="button"
            @pointerdown.prevent="startInteractiveInhale"
            @pointerup.prevent="completeInteractiveBreath"
            @pointercancel="cancelInteractiveInhale"
            @keydown.space.prevent="startInteractiveInhale"
            @keyup.space.prevent="completeInteractiveBreath"
            @keydown.enter.prevent="startInteractiveInhale"
            @keyup.enter.prevent="completeInteractiveBreath"
          >
            <span>{{ breathingHolding ? 'Keep holding' : 'Press & hold' }}</span>
            <small>{{ breathingHolding ? 'Breathe in' : 'Then release to breathe out' }}</small>
          </button>
          <h1 id="exercise-title">{{ interactiveBreathingLabel }}</h1>
          <p>{{ breathingHolding ? 'Keep the button held for as long as your inhale feels comfortable.' : 'Press again when you are ready for the next breath.' }}</p>
        </template>

        <template v-else>
          <div class="breathing-orb" :class="[currentBreathingPhase.className, { paused: breathingPaused }]" aria-hidden="true"></div>
          <h1 id="exercise-title">{{ currentBreathingPhase.label }}</h1>
          <p>Let the rhythm guide you without forcing the breath. Keep both feet supported if that feels comfortable.</p>
        </template>

        <template v-if="breathingMode">
          <div
            class="breathing-progress-bar"
            role="progressbar"
            aria-label="Breathing exercise progress"
            aria-valuemin="0"
            aria-valuemax="100"
            :aria-valuenow="Math.round(breathingProgress)"
          >
            <span :style="{ width: `${breathingProgress}%` }"></span>
          </div>
          <div class="breath-progress" :aria-label="`${breathingRound} of 4 breathing rounds complete`">
            <i v-for="round in 4" :key="round" :class="{ complete: round - 1 < breathingRound }"></i>
          </div>
          <div class="breathing-controls">
            <button v-if="breathingMode === 'timer'" class="secondary-button" type="button" @click="toggleBreathingPause">
              {{ breathingPaused ? 'Resume' : 'Pause' }}
            </button>
            <button class="text-button" type="button" @click="chooseBreathingMethod">Choose another method</button>
          </div>
        </template>
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

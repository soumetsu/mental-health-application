<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import chatbotCopy from '../data/chatbot.json'
import { api } from '../services/api'
import { createVoiceSession } from '../services/voiceSession'

const props = defineProps({
  token: { type: String, required: true },
  readAloud: { type: Boolean, default: false },
  voiceInput: { type: Boolean, default: false },
})
const emit = defineEmits(['navigate'])
const open = ref(false)
const message = ref('')
const pending = ref(false)
const loadingHistory = ref(false)
const clearingHistory = ref(false)
const chatBusy = computed(() => pending.value || loadingHistory.value || clearingHistory.value)
const error = ref('')
const sessionId = ref(0)
const initialMessages = () => [{ role: 'assistant', content: chatbotCopy.intro }]
const retainedMessageCount = 50
const messages = ref(initialMessages())
const contextUsed = ref(null)
const listElement = ref(null)
const chatLauncher = ref(null)
const chatCloseButton = ref(null)
const speechLanguage = document.documentElement.lang || 'en-US'
const speakingIndex = ref(-1)
const voiceSetupOpen = ref(false)
const voiceState = ref({ phase: 'idle', mode: 'conversation' })
const voiceActive = computed(() => voiceState.value.phase !== 'idle')
const conversationMode = computed(() => voiceActive.value && voiceState.value.mode === 'conversation')
const listening = computed(() => ['starting', 'listening'].includes(voiceState.value.phase))
const voiceStatus = computed(() => ({ starting: 'Opening microphone…', listening: 'Listening — speak naturally.', thinking: 'AI is composing a reply…', speaking: 'Reading the AI reply — microphone is off.' })[voiceState.value.phase] || '')
const speechAvailable = typeof window !== 'undefined' && 'speechSynthesis' in window
const Recognition = typeof window !== 'undefined'
  ? window.SpeechRecognition || window.webkitSpeechRecognition
  : null
const recognitionAvailable = Boolean(Recognition)
const voice = createVoiceSession({
  Recognition,
  synthesis: speechAvailable ? window.speechSynthesis : null,
  Utterance: typeof window !== 'undefined' ? window.SpeechSynthesisUtterance : null,
  send: (text) => send(text, true),
  onState: (state) => { voiceState.value = state },
  onTranscript: (text) => { message.value = text },
  onError: (text) => { error.value = text },
  language: speechLanguage,
})

const quickPrompts = chatbotCopy.quickPrompts
const actionMarkers = [
  { marker: '[[OPEN_CHECKIN]]', destination: 'checkin', label: 'Open check-in' },
  { marker: '[[OPEN_EXERCISES]]', destination: 'exercises', label: 'Open exercises' },
]

function assistantMessage(content) {
  const action = actionMarkers.find((item) => content.includes(item.marker))
  const cleanContent = actionMarkers.reduce(
    (text, item) => text.replaceAll(item.marker, ''),
    content,
  ).trim()
  return { role: 'assistant', content: cleanContent, action }
}

async function toggleChat() {
  if (open.value) {
    closeChat()
    return
  }
  open.value = true
  nextTick(() => chatCloseButton.value?.focus())
  if (chatBusy.value) return
  loadingHistory.value = true
  error.value = ''
  const activeSession = sessionId.value
  try {
    const turns = await api.chatHistory(props.token)
    if (activeSession !== sessionId.value) return
    messages.value = [
      ...initialMessages(),
      ...turns.flatMap((turn) => [
        { role: 'user', content: turn.message },
        assistantMessage(turn.reply),
      ]),
    ]
    contextUsed.value = null
  } catch {
    if (activeSession === sessionId.value) error.value = 'Could not load saved chat. Reopen chat to try again.'
  } finally {
    if (activeSession === sessionId.value) {
      loadingHistory.value = false
      await scrollToEnd()
    }
  }
}

function closeChat(restoreFocus = true) {
  open.value = false
  stopVoiceFeatures()
  if (restoreFocus) nextTick(() => chatLauncher.value?.focus())
}

async function clearHistory() {
  if (chatBusy.value || !window.confirm('Clear the saved conversation for this account?')) return
  stopVoiceFeatures()
  clearingHistory.value = true
  error.value = ''
  const activeSession = sessionId.value
  try {
    await api.clearChatHistory(props.token)
    if (activeSession !== sessionId.value) return
    messages.value = initialMessages()
    message.value = ''
    contextUsed.value = null
  } catch (reason) {
    if (activeSession === sessionId.value) error.value = reason.message
  } finally {
    if (activeSession === sessionId.value) clearingHistory.value = false
  }
}

async function send(text = message.value, fromVoice = false) {
  const clean = text.trim()
  if (!clean || chatBusy.value) return
  if (clean.length > 1200) { error.value = 'Keep your message to 1,200 characters or fewer.'; return }
  if (!fromVoice) stopVoiceFeatures()
  error.value = ''
  messages.value.push({ role: 'user', content: clean })
  message.value = ''
  pending.value = true
  const activeSession = sessionId.value
  await scrollToEnd()
  try {
    if (activeSession !== sessionId.value) return
    const history = messages.value.slice(1, -1)
      .filter(({ content }) => content)
      .slice(-10)
      .map(({ role, content }) => ({ role, content: content.slice(0, 1200) }))
    const response = await api.sendChatMessage(props.token, clean, history)
    if (activeSession !== sessionId.value) return
    const reply = assistantMessage(response.reply)
    messages.value = [...initialMessages(), ...messages.value.slice(1).concat(reply).slice(-retainedMessageCount)]
    const replyIndex = messages.value.length - 1
    contextUsed.value = response.context_used
    if (!response.history_saved) error.value = 'The reply is available, but this exchange could not be saved.'
    if (open.value && props.readAloud && !fromVoice) speak(reply.content, replyIndex)
    return reply.content
  } catch (reason) {
    if (activeSession !== sessionId.value) return
    messages.value.pop()
    if (!message.value) message.value = clean
    error.value = reason.message
    if (fromVoice) throw reason
  } finally {
    if (activeSession === sessionId.value) {
      pending.value = false
      await scrollToEnd()
    }
  }
}

function stopSpeaking() {
  if (speechAvailable) window.speechSynthesis.cancel()
  speakingIndex.value = -1
}

function speak(text, index) {
  if (!speechAvailable || !text) return
  voice.stop()
  stopSpeaking()
  const utterance = new SpeechSynthesisUtterance(text)
  utterance.rate = 0.95
  utterance.onend = () => {
    speakingIndex.value = -1
  }
  utterance.onerror = () => { speakingIndex.value = -1 }
  speakingIndex.value = index
  window.speechSynthesis.speak(utterance)
}

function toggleDictation() {
  if (voiceActive.value) stopVoiceFeatures()
  else {
    stopSpeaking()
    error.value = ''
    voice.start('dictation')
  }
}

function startVoiceConversation() {
  if (chatBusy.value) return
  stopSpeaking()
  error.value = ''
  voiceSetupOpen.value = false
  voice.start('conversation')
}

function stopVoiceFeatures() {
  voiceSetupOpen.value = false
  voice.stop()
  stopSpeaking()
}

function handleVisibilityChange() {
  if (document.hidden) stopVoiceFeatures()
}
document.addEventListener('visibilitychange', handleVisibilityChange)

function navigateTo(destination) {
  closeChat(false)
  emit('navigate', destination)
}

async function scrollToEnd() {
  await nextTick()
  listElement.value?.scrollTo({ top: listElement.value.scrollHeight, behavior: 'smooth' })
}

watch(() => props.voiceInput, (enabled) => {
  if (!enabled) stopVoiceFeatures()
})

onBeforeUnmount(() => {
  sessionId.value += 1
  stopVoiceFeatures()
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>

<template>
  <button
    v-if="!open"
    ref="chatLauncher"
    class="chat-bubble"
    type="button"
    :aria-expanded="open"
    aria-controls="support-chat-window"
    aria-label="Open support chat"
    @click="toggleChat"
  >
    <span aria-hidden="true">✦</span>
  </button>

  <section v-if="open" id="support-chat-window" class="chat-window" role="dialog" aria-modal="false" aria-labelledby="chat-title" @keydown.esc.stop="closeChat()">
    <header class="chat-header">
      <div>
        <p class="eyebrow">{{ chatbotCopy.eyebrow }}</p>
        <h2 id="chat-title">{{ chatbotCopy.name }}</h2>
      </div>
      <button ref="chatCloseButton" class="icon-button" type="button" aria-label="Close support chat" @click="closeChat()">×</button>
    </header>

    <details class="chat-disclosure" open>
      <summary>About chat and privacy</summary>
      <p>{{ chatbotCopy.disclosure }} {{ chatbotCopy.historyDisclosure }}</p>
      <button class="text-button clear-chat-button" type="button" :disabled="chatBusy" @click="clearHistory">
        {{ clearingHistory ? 'Clearing…' : 'Clear saved chat' }}
      </button>
    </details>

    <div ref="listElement" class="chat-messages" aria-live="polite">
      <p v-if="loadingHistory" role="status">Loading saved chat…</p>
      <article v-for="(item, index) in messages" :key="index" class="chat-message" :class="item.role">
        <span>{{ item.role === 'assistant' ? chatbotCopy.name : 'You' }}</span>
        <p>{{ item.content }}</p>
        <button
          v-if="item.role === 'assistant' && speechAvailable"
          class="chat-speech-button"
          type="button"
          :aria-label="speakingIndex === index ? 'Stop reading this reply' : 'Read this reply aloud'"
          @click="speakingIndex === index ? stopSpeaking() : speak(item.content, index)"
        >{{ speakingIndex === index ? '■ Stop' : '◖ Read aloud' }}</button>
        <button v-if="item.action" class="chat-action-link" type="button" @click="navigateTo(item.action.destination)">
          {{ item.action.label }} →
        </button>
      </article>
      <article v-if="pending" class="chat-message assistant pending-message" role="status">
        <span>{{ chatbotCopy.name }}</span><p>Thinking<span aria-hidden="true">…</span></p>
      </article>
      <section v-if="voiceSetupOpen" id="voice-session-setup" class="voice-session-setup" aria-labelledby="voice-session-title">
        <h3 id="voice-session-title">Talk with Mindful chat</h3>
        <template v-if="recognitionAvailable && speechAvailable">
          <p>{{ chatbotCopy.voiceSessionIntro }}</p>
          <p>{{ chatbotCopy.voiceDisclosure }}</p>
          <p>{{ chatbotCopy.voiceSessionSending }}</p>
          <div class="button-row">
            <button class="text-button" type="button" @click="voiceSetupOpen = false">Cancel</button>
            <button class="primary-button small" type="button" :disabled="chatBusy" @click="startVoiceConversation">Start browser microphone</button>
          </div>
        </template>
        <template v-else>
          <p role="status">{{ chatbotCopy.voiceUnavailable }}</p>
        </template>
      </section>
    </div>

    <div v-if="!chatBusy && !voiceActive && messages.length === 1 && !message.length" class="quick-prompts" aria-label="Suggested messages">
      <button v-for="prompt in quickPrompts" :key="prompt" type="button" :disabled="voiceActive || chatBusy" @click="send(prompt)">{{ prompt }}</button>
    </div>
    <div class="voice-session-entry">
      <button v-if="!voiceActive" class="voice-session-button" type="button" :disabled="chatBusy" :aria-expanded="voiceSetupOpen" aria-controls="voice-session-setup" @click="voiceSetupOpen = !voiceSetupOpen; scrollToEnd()">
        <span aria-hidden="true">◉</span> Try an AI voice session
      </button>
      <template v-else>
        <p class="voice-session-status" role="status"><span aria-hidden="true">●</span> {{ voiceStatus }}</p>
        <button class="voice-session-button stop" type="button" @click="stopVoiceFeatures">■ Stop voice session</button>
      </template>
    </div>

    <p v-if="contextUsed" class="context-note">
      Recent context used: {{ contextUsed.events }} events, {{ contextUsed.check_ins }} check-ins, {{ contextUsed.exercises }} exercises.
    </p>
    <p v-if="error" class="form-error chat-error" role="alert">{{ error }}</p>
    <div v-if="voiceInput && recognitionAvailable" class="voice-controls" aria-label="Voice controls">
      <button class="text-button" type="button" :disabled="conversationMode || chatBusy" :aria-pressed="listening && !conversationMode" @click="toggleDictation">
        {{ listening ? '■ Stop listening' : '● Dictate message' }}
      </button>
      <span v-if="listening" role="status">Listening…</span>
    </div>
    <p v-if="voiceInput && recognitionAvailable" class="voice-disclosure">{{ chatbotCopy.voiceDisclosure }}</p>

    <form class="chat-form" @submit.prevent="send()">
      <label class="sr-only" for="chat-message">Message</label>
      <textarea id="chat-message" v-model="message" :readonly="voiceActive" maxlength="1200" rows="2" :placeholder="listening ? 'Listening…' : 'Write a message…'" @keydown.enter.exact.prevent="!voiceActive && send()"></textarea>
      <button class="primary-button" type="submit" :disabled="chatBusy || voiceActive || !message.trim()">Send</button>
    </form>

    <p class="chat-crisis-note">{{ chatbotCopy.crisisNote }}</p>
  </section>
</template>

<script setup>
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import chatbotCopy from '../data/chatbot.json'
import { api } from '../services/api'

const props = defineProps({
  token: { type: String, required: true },
  readAloud: { type: Boolean, default: false },
  voiceInput: { type: Boolean, default: false },
})
const emit = defineEmits(['navigate'])
const open = ref(false)
const message = ref('')
const pending = ref(false)
const error = ref('')
const sessionId = ref(0)
const initialMessages = () => [{ role: 'assistant', content: chatbotCopy.intro }]
const messages = ref(initialMessages())
const contextUsed = ref(null)
const listElement = ref(null)
const speakingIndex = ref(-1)
const listening = ref(false)
const conversationMode = ref(false)
const speechAvailable = typeof window !== 'undefined' && 'speechSynthesis' in window
const Recognition = typeof window !== 'undefined'
  ? window.SpeechRecognition || window.webkitSpeechRecognition
  : null
const recognitionAvailable = Boolean(Recognition)
let recognition

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

function toggleChat() {
  open.value = !open.value
  sessionId.value += 1
  if (open.value) {
    messages.value = initialMessages()
    message.value = ''
    pending.value = false
    error.value = ''
    contextUsed.value = null
  } else {
    stopVoiceFeatures()
  }
}

function closeChat() {
  open.value = false
  sessionId.value += 1
  stopVoiceFeatures()
}

async function send(text = message.value) {
  const clean = text.trim()
  if (!clean || pending.value) return
  error.value = ''
  messages.value.push({ role: 'user', content: clean })
  message.value = ''
  pending.value = true
  const activeSession = sessionId.value
  await scrollToEnd()
  try {
    const history = messages.value.slice(1, -1).slice(-10).map(({ role, content }) => ({ role, content }))
    const response = await api.sendChatMessage(props.token, clean, history)
    if (activeSession !== sessionId.value) return
    const reply = assistantMessage(response.reply)
    messages.value.push(reply)
    const replyIndex = messages.value.length - 1
    contextUsed.value = response.context_used
    if (props.readAloud || conversationMode.value) speak(reply.content, replyIndex, conversationMode.value)
  } catch (reason) {
    if (activeSession !== sessionId.value) return
    error.value = reason.message
    conversationMode.value = false
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

function speak(text, index, continueConversation = false) {
  if (!speechAvailable || !text) return
  stopSpeaking()
  const utterance = new SpeechSynthesisUtterance(text)
  utterance.rate = 0.95
  utterance.onend = () => {
    speakingIndex.value = -1
    if (continueConversation && conversationMode.value) startListening(true)
  }
  utterance.onerror = () => { speakingIndex.value = -1 }
  speakingIndex.value = index
  window.speechSynthesis.speak(utterance)
}

function stopListening() {
  recognition?.abort()
  recognition = null
  listening.value = false
}

function startListening(sendWhenFinal = false) {
  if (!recognitionAvailable || listening.value || pending.value) return
  error.value = ''
  recognition = new Recognition()
  recognition.continuous = false
  recognition.interimResults = true
  recognition.lang = document.documentElement.lang || 'en-US'
  recognition.onstart = () => { listening.value = true }
  recognition.onresult = (event) => {
    let transcript = ''
    let isFinal = false
    for (let index = event.resultIndex; index < event.results.length; index += 1) {
      transcript += event.results[index][0].transcript
      isFinal ||= event.results[index].isFinal
    }
    message.value = transcript.trimStart()
    if (isFinal && sendWhenFinal && message.value.trim()) {
      listening.value = false
      send(message.value)
    }
  }
  recognition.onerror = (event) => {
    listening.value = false
    if (!['aborted', 'no-speech'].includes(event.error)) {
      error.value = event.error === 'not-allowed'
        ? 'Microphone access was not allowed. You can continue by typing.'
        : 'Voice input stopped. You can continue by typing.'
      conversationMode.value = false
    }
  }
  recognition.onend = () => {
    listening.value = false
    recognition = null
  }
  try {
    recognition.start()
  } catch {
    error.value = 'Voice input could not start. You can continue by typing.'
    conversationMode.value = false
  }
}

function toggleDictation() {
  if (listening.value) stopListening()
  else startListening(false)
}

function toggleConversation() {
  if (conversationMode.value) {
    conversationMode.value = false
    stopSpeaking()
    stopListening()
    return
  }
  if (!recognitionAvailable || !speechAvailable) {
    error.value = 'Conversation mode is not available in this browser.'
    return
  }
  conversationMode.value = true
  startListening(true)
}

function stopVoiceFeatures() {
  conversationMode.value = false
  stopSpeaking()
  stopListening()
}

function navigateTo(destination) {
  closeChat()
  emit('navigate', destination)
}

async function scrollToEnd() {
  await nextTick()
  listElement.value?.scrollTo({ top: listElement.value.scrollHeight, behavior: 'smooth' })
}

watch(() => props.voiceInput, (enabled) => {
  if (!enabled) stopVoiceFeatures()
})

onBeforeUnmount(stopVoiceFeatures)
</script>

<template>
  <button
    class="chat-bubble"
    :class="{ open }"
    type="button"
    :aria-expanded="open"
    aria-controls="support-chat-window"
    aria-label="Open support chat"
    @click="toggleChat"
  >
    <span aria-hidden="true">{{ open ? '×' : '✦' }}</span>
  </button>

  <section v-if="open" id="support-chat-window" class="chat-window" role="dialog" aria-modal="false" aria-labelledby="chat-title">
    <header class="chat-header">
      <div>
        <p class="eyebrow">{{ chatbotCopy.eyebrow }}</p>
        <h2 id="chat-title">{{ chatbotCopy.name }}</h2>
      </div>
      <button class="icon-button" type="button" aria-label="Close support chat" @click="closeChat">×</button>
    </header>

    <p class="chat-disclosure">
      {{ chatbotCopy.disclosure }}
    </p>

    <div ref="listElement" class="chat-messages" aria-live="polite">
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
    </div>

    <div v-if="messages.length === 1" class="quick-prompts" aria-label="Suggested messages">
      <button v-for="prompt in quickPrompts" :key="prompt" type="button" @click="send(prompt)">{{ prompt }}</button>
    </div>

    <p v-if="contextUsed" class="context-note">
      Recent context used: {{ contextUsed.events }} events, {{ contextUsed.check_ins }} check-ins, {{ contextUsed.exercises }} exercises.
    </p>
    <p v-if="error" class="form-error chat-error" role="alert">{{ error }}</p>

    <div v-if="voiceInput && recognitionAvailable" class="voice-controls" aria-label="Voice controls">
      <button class="secondary-button small" type="button" :aria-pressed="conversationMode" @click="toggleConversation">
        {{ conversationMode ? 'Stop conversation' : 'Conversation mode' }}
      </button>
      <button class="text-button" type="button" :disabled="conversationMode" :aria-pressed="listening" @click="toggleDictation">
        {{ listening ? '■ Stop listening' : '● Dictate message' }}
      </button>
      <span v-if="listening" role="status">Listening…</span>
    </div>
    <p v-if="voiceInput && recognitionAvailable" class="voice-disclosure">{{ chatbotCopy.voiceDisclosure }}</p>

    <form class="chat-form" @submit.prevent="send()">
      <label class="sr-only" for="chat-message">Message</label>
      <textarea id="chat-message" v-model="message" maxlength="1200" rows="2" :placeholder="listening ? 'Listening…' : 'Write a message…'" @keydown.enter.exact.prevent="send()"></textarea>
      <button class="primary-button" type="submit" :disabled="pending || !message.trim()">Send</button>
    </form>

    <p class="chat-crisis-note">{{ chatbotCopy.crisisNote }}</p>
  </section>
</template>

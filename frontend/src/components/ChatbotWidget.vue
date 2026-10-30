<script setup>
import { nextTick, ref } from 'vue'
import chatbotCopy from '../data/chatbot.json'
import { api } from '../services/api'

const props = defineProps({ token: { type: String, required: true } })
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
  }
}

function closeChat() {
  open.value = false
  sessionId.value += 1
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
    messages.value.push(assistantMessage(response.reply))
    contextUsed.value = response.context_used
  } catch (reason) {
    if (activeSession !== sessionId.value) return
    error.value = reason.message
  } finally {
    if (activeSession === sessionId.value) {
      pending.value = false
      await scrollToEnd()
    }
  }
}

function navigateTo(destination) {
  closeChat()
  emit('navigate', destination)
}

async function scrollToEnd() {
  await nextTick()
  listElement.value?.scrollTo({ top: listElement.value.scrollHeight, behavior: 'smooth' })
}
</script>

<template>
  <button
    class="chat-bubble"
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

    <form class="chat-form" @submit.prevent="send()">
      <label class="sr-only" for="chat-message">Message</label>
      <textarea id="chat-message" v-model="message" maxlength="1200" rows="2" placeholder="Write a message…" @keydown.enter.exact.prevent="send()"></textarea>
      <button class="primary-button" type="submit" :disabled="pending || !message.trim()">Send</button>
    </form>

    <p class="chat-crisis-note">{{ chatbotCopy.crisisNote }}</p>
  </section>
</template>

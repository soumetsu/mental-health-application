<script setup>
import { onBeforeUnmount, ref } from 'vue'

const available = typeof window !== 'undefined' && 'speechSynthesis' in window
const speaking = ref(false)

function stop() {
  if (available) window.speechSynthesis.cancel()
  speaking.value = false
}

function toggle() {
  if (!available) return
  if (speaking.value) {
    stop()
    return
  }
  const text = document.querySelector('main')?.innerText?.trim()
  if (!text) return
  const utterance = new SpeechSynthesisUtterance(text)
  utterance.rate = 0.95
  utterance.onend = () => { speaking.value = false }
  utterance.onerror = () => { speaking.value = false }
  window.speechSynthesis.cancel()
  window.speechSynthesis.speak(utterance)
  speaking.value = true
}

onBeforeUnmount(stop)
</script>

<template>
  <button v-if="available" class="text-button read-page-button" type="button" :aria-pressed="speaking" @click="toggle">
    <span aria-hidden="true">{{ speaking ? '■' : '◖' }}</span>
    <b>{{ speaking ? 'Stop reading' : 'Read page' }}</b>
  </button>
</template>

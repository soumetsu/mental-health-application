<script setup>
import { computed, ref } from 'vue'

const props = defineProps({ events: { type: Array, default: () => [] } })
const emit = defineEmits(['add', 'delete'])
const cursor = ref(new Date())

const monthKey = computed(() => `${cursor.value.getFullYear()}-${String(cursor.value.getMonth() + 1).padStart(2, '0')}`)
const monthLabel = computed(() => cursor.value.toLocaleDateString(undefined, { month: 'long', year: 'numeric' }))
const days = computed(() => {
  const year = cursor.value.getFullYear()
  const month = cursor.value.getMonth()
  const offset = new Date(year, month, 1).getDay()
  const count = new Date(year, month + 1, 0).getDate()
  return [...Array(offset).fill(null), ...Array.from({ length: count }, (_, index) => index + 1)]
})
const monthEvents = computed(() => props.events.filter((item) => item.happened_on.startsWith(monthKey.value)))

function moveMonth(amount) {
  cursor.value = new Date(cursor.value.getFullYear(), cursor.value.getMonth() + amount, 1)
}

function eventsFor(day) {
  const key = `${monthKey.value}-${String(day).padStart(2, '0')}`
  return monthEvents.value.filter((item) => item.happened_on === key)
}

function requestDelete(item) {
  if (window.confirm(`Delete “${item.title}”? This cannot be undone.`)) emit('delete', item.id)
}
</script>

<template>
  <section class="calendar-card" aria-labelledby="calendar-title">
    <img class="figma-calendar-motif" src="/figma-calendar.png" alt="" width="112" height="111" aria-hidden="true" />
    <div class="section-heading">
      <div><p class="eyebrow">Your event log</p><h2 id="calendar-title">{{ monthLabel }}</h2></div>
      <button class="secondary-button small" type="button" @click="emit('add')">+ Add event</button>
    </div>
    <div class="calendar-controls">
      <button aria-label="Previous month" type="button" @click="moveMonth(-1)">←</button>
      <span class="legend"><i class="positive"></i>Positive <i class="negative"></i>Difficult <i class="neutral"></i>Neutral</span>
      <button aria-label="Next month" type="button" @click="moveMonth(1)">→</button>
    </div>
    <div class="calendar-grid" aria-label="Monthly event calendar">
      <span v-for="(dayName, index) in ['S','M','T','W','T','F','S']" :key="index" class="weekday">{{ dayName }}</span>
      <div v-for="(day, index) in days" :key="index" class="calendar-day" :class="{ empty: !day }">
        <span v-if="day">{{ day }}</span>
        <div v-if="day" class="day-dots"><i v-for="event in eventsFor(day).slice(0, 3)" :key="event.id" :class="event.valence" :title="event.title"></i></div>
      </div>
    </div>
    <div class="event-list">
      <p v-if="monthEvents.length === 0" class="empty-state">No events logged this month. Add only what feels useful.</p>
      <article v-for="item in monthEvents" :key="item.id" class="event-item">
        <i :class="item.valence" aria-hidden="true"></i>
        <div><strong>{{ item.title }}</strong><span>{{ new Date(`${item.happened_on}T12:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) }} · impact {{ item.intensity }}/5</span></div>
        <button class="icon-button" type="button" :aria-label="`Delete ${item.title}`" @click="requestDelete(item)">×</button>
      </article>
    </div>
  </section>
</template>


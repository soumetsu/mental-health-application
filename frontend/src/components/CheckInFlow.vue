<script setup>
import { reactive, ref } from 'vue'
import { api } from '../services/api'

const props = defineProps({ token: { type: String, required: true } })
const emit = defineEmits(['complete', 'cancel'])
const step = ref(1)
const busy = ref(false)
const error = ref('')
const form = reactive({ mood: null, energy: null, note: '', tags: [] })
const tags = ['work', 'school', 'relationships', 'body', 'rest', 'something else']

async function finish() {
  busy.value = true
  error.value = ''
  try {
    await api.createCheckIn(props.token, form)
    step.value = 3
  } catch (reason) {
    error.value = reason.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section class="flow-card checkin" aria-labelledby="checkin-title">
    <button class="text-button back-button" type="button" @click="emit('cancel')">← Leave check-in</button>
    <div class="flow-heading">
      <div><p class="eyebrow">Daily check-in</p><h1 id="checkin-title">A moment for you</h1></div>
      <span>{{ step < 3 ? `${step} / 2` : 'Done' }}</span>
    </div>
    <div class="progress-track"><span :style="{ width: `${step < 3 ? step * 50 : 100}%` }"></span></div>

    <div v-if="step === 1" class="question-stage">
      <fieldset class="choice-fieldset">
        <legend>How does this moment feel?</legend>
        <p>Choose the closest fit. There is no wrong answer.</p>
        <div class="mood-options">
          <label v-for="item in [{v:1,e:'😞',l:'Rough'}, {v:2,e:'😕',l:'Low'}, {v:3,e:'😐',l:'Okay'}, {v:4,e:'🙂',l:'Good'}, {v:5,e:'😊',l:'Bright'}]" :key="item.v">
            <input v-model.number="form.mood" type="radio" :value="item.v" />
            <span><b aria-hidden="true">{{ item.e }}</b>{{ item.l }}</span>
          </label>
        </div>
      </fieldset>
      <label>
        Want to put it into words? <span class="optional">optional</span>
        <textarea v-model="form.note" maxlength="600" rows="4" placeholder="A sentence is enough."></textarea>
      </label>
      <div class="button-row end"><button class="primary-button" :disabled="!form.mood" type="button" @click="step = 2">Continue</button></div>
    </div>

    <form v-else-if="step === 2" class="question-stage" @submit.prevent="finish">
      <fieldset class="choice-fieldset">
        <legend>How much energy do you have?</legend>
        <div class="energy-options">
          <label v-for="level in 5" :key="level"><input v-model.number="form.energy" type="radio" :value="level" /><span>{{ level }}</span></label>
        </div>
        <div class="scale-labels"><span>Very little</span><span>A lot</span></div>
      </fieldset>
      <fieldset class="choice-fieldset">
        <legend>What is part of today? <span class="optional">optional</span></legend>
        <div class="chip-grid">
          <label v-for="tag in tags" :key="tag" class="choice-chip"><input v-model="form.tags" type="checkbox" :value="tag" /><span>{{ tag }}</span></label>
        </div>
      </fieldset>
      <p class="form-error" v-if="error" role="alert">{{ error }}</p>
      <div class="button-row"><button class="secondary-button" type="button" @click="step = 1">Back</button><button class="primary-button" :disabled="!form.energy || busy" type="submit">{{ busy ? 'Saving…' : 'Finish check-in' }}</button></div>
    </form>

    <div v-else class="completion-panel" role="status">
      <div class="completion-art" aria-hidden="true">✦</div>
      <p class="eyebrow">Check-in complete</p>
      <h2>Thank you for noticing what is here.</h2>
      <p>You do not need to fix everything right now. Your check-in is saved privately to this local prototype.</p>
      <button class="primary-button" type="button" @click="emit('complete')">Return home</button>
    </div>
  </section>
</template>


<script setup>
import { reactive, ref } from 'vue'

const emit = defineEmits(['save'])
defineProps({ busy: Boolean, error: { type: String, default: '' } })

const stressorOptions = ['School', 'Work', 'Relationships', 'Health', 'Finances', 'Change']
const form = reactive({ stressors: [], sleep_hours: 7, support_style: 'balanced' })
const step = ref(1)
</script>

<template>
  <section class="flow-card onboarding" aria-labelledby="onboarding-title">
    <div class="flow-heading">
      <div>
        <p class="eyebrow">A gentle start</p>
        <h1 id="onboarding-title">What would make this space useful?</h1>
      </div>
      <span>{{ step }} / 2</span>
    </div>
    <div class="progress-track" aria-hidden="true"><span :style="{ width: `${step * 50}%` }"></span></div>

    <div v-if="step === 1">
      <fieldset class="choice-fieldset">
        <legend>What tends to take up your energy?</legend>
        <p>Choose any. You can change this later.</p>
        <div class="chip-grid">
          <label v-for="option in stressorOptions" :key="option" class="choice-chip">
            <input v-model="form.stressors" type="checkbox" :value="option.toLowerCase()" />
            <span>{{ option }}</span>
          </label>
        </div>
      </fieldset>
      <label class="range-label">
        About how many hours do you usually sleep? <strong>{{ form.sleep_hours }}</strong>
        <input v-model.number="form.sleep_hours" type="range" min="0" max="12" step="0.5" />
      </label>
      <button class="primary-button" type="button" @click="step = 2">Next</button>
    </div>

    <form v-else @submit.prevent="emit('save', form)">
      <fieldset class="choice-fieldset">
        <legend>How present should the app feel?</legend>
        <div class="radio-stack">
          <label><input v-model="form.support_style" type="radio" value="quiet" /><span><strong>Quiet</strong>Keep suggestions tucked away.</span></label>
          <label><input v-model="form.support_style" type="radio" value="balanced" /><span><strong>Balanced</strong>Offer a next step when it may help.</span></label>
          <label><input v-model="form.support_style" type="radio" value="encouraging" /><span><strong>Encouraging</strong>Use a little more positive reinforcement.</span></label>
        </div>
      </fieldset>
      <p class="form-error" v-if="error" role="alert">{{ error }}</p>
      <div class="button-row">
        <button class="secondary-button" type="button" @click="step = 1">Back</button>
        <button class="primary-button" :disabled="busy" type="submit">{{ busy ? 'Saving…' : 'Finish setup' }}</button>
      </div>
    </form>
  </section>
</template>


<script setup>
import { computed } from 'vue'

const props = defineProps({
  avatarKey: { type: String, default: 'leaf' },
  avatarImage: { type: String, default: '' },
})

const avatarAsset = computed(() => `/avatars/${['leaf', 'moon', 'tea', 'fox'].includes(props.avatarKey) ? props.avatarKey : 'leaf'}.png`)
</script>

<template>
  <span class="profile-avatar" aria-hidden="true">
    <img :src="avatarImage || avatarAsset" alt="" />
  </span>
</template>

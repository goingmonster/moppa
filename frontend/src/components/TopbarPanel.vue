<script setup lang="ts">
defineProps<{
  currentUserLabel: string
  isAuthenticated: boolean
}>()

const emit = defineEmits<{
  (e: 'open-auth'): void
  (e: 'logout'): void
}>()
</script>

<template>
  <header class="topbar panel">
    <div class="topbar-title">
      <h1>模型预测指挥甲板</h1>
    </div>
    <div class="topbar-meta">
      <div class="topbar-auth">
        <span class="chip">当前用户：{{ currentUserLabel }}</span>
        <button v-if="!isAuthenticated" class="action-btn mini-btn" @click="emit('open-auth')">登录</button>
        <button v-else class="action-btn mini-btn" @click="emit('logout')">退出登录</button>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
defineProps<{
  currentUserLabel: string
  isAuthenticated: boolean
  activeTheme: string
  themeOptions: Array<{ id: string; label: string }>
}>()

const emit = defineEmits<{
  (e: 'open-auth'): void
  (e: 'logout'): void
  (e: 'update-theme', value: string): void
}>()

function handleThemeChange(event: Event): void {
  const target = event.target
  if (!(target instanceof HTMLSelectElement)) {
    return
  }
  emit('update-theme', target.value)
}
</script>

<template>
  <header class="topbar panel">
    <div class="topbar-title">
      <h1>模型预测指挥甲板</h1>
    </div>
    <div class="topbar-meta">
      <div class="topbar-auth">
        <label class="theme-switch">
          <span>主题</span>
          <select :value="activeTheme" @change="handleThemeChange">
            <option v-for="item in themeOptions" :key="item.id" :value="item.id">{{ item.label }}</option>
          </select>
        </label>
        <span class="chip">当前用户：{{ currentUserLabel }}</span>
        <button v-if="!isAuthenticated" class="action-btn mini-btn" @click="emit('open-auth')">登录</button>
        <button v-else class="action-btn mini-btn" @click="emit('logout')">退出登录</button>
      </div>
    </div>
  </header>
</template>

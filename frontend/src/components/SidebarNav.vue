<script setup lang="ts">
type AppView = 'home' | 'events' | 'questions' | 'questionStream' | 'templates' | 'tasks' | 'dataSources' | 'filterRules' | 'apiKeys' | 'modelEndpoints'

defineProps<{
  currentView: AppView
  isAdmin: boolean
}>()

const emit = defineEmits<{
  (e: 'update:view', value: AppView): void
}>()
</script>

<template>
  <aside class="panel nav-panel sidebar-nav">
    <div class="panel-head">
      <h2>模块导航</h2>
    </div>
    <nav class="view-switch" aria-label="主模块导航">
      <div class="nav-group">
        <p class="nav-group-title">概览</p>
        <button type="button" :class="['level-btn', { active: currentView === 'home' }]" :aria-pressed="currentView === 'home'" @click="emit('update:view', 'home')">首页总览</button>
      </div>
      <div class="nav-group">
        <p class="nav-group-title">核心管理</p>
        <button type="button" :class="['level-btn', { active: currentView === 'questionStream' }]" :aria-pressed="currentView === 'questionStream'" @click="emit('update:view', 'questionStream')">问题社区</button>
        <button v-if="isAdmin" type="button" :class="['level-btn', { active: currentView === 'events' }]" :aria-pressed="currentView === 'events'" @click="emit('update:view', 'events')">事件管理</button>
        <button v-if="isAdmin" type="button" :class="['level-btn', { active: currentView === 'questions' }]" :aria-pressed="currentView === 'questions'" @click="emit('update:view', 'questions')">问题管理</button>
        <button v-if="isAdmin" type="button" :class="['level-btn', { active: currentView === 'templates' }]" :aria-pressed="currentView === 'templates'" @click="emit('update:view', 'templates')">模板配置</button>
        <button v-if="isAdmin" type="button" :class="['level-btn', { active: currentView === 'tasks' }]" :aria-pressed="currentView === 'tasks'" @click="emit('update:view', 'tasks')">任务管理</button>
      </div>
      <div v-if="isAdmin" class="nav-group">
        <p class="nav-group-title">系统配置</p>
        <button type="button" :class="['level-btn', { active: currentView === 'dataSources' }]" :aria-pressed="currentView === 'dataSources'" @click="emit('update:view', 'dataSources')">数据源管理</button>
        <button type="button" :class="['level-btn', { active: currentView === 'filterRules' }]" :aria-pressed="currentView === 'filterRules'" @click="emit('update:view', 'filterRules')">过滤规则管理</button>
        <button type="button" :class="['level-btn', { active: currentView === 'apiKeys' }]" :aria-pressed="currentView === 'apiKeys'" @click="emit('update:view', 'apiKeys')">身份认证</button>
        <button type="button" :class="['level-btn', { active: currentView === 'modelEndpoints' }]" :aria-pressed="currentView === 'modelEndpoints'" @click="emit('update:view', 'modelEndpoints')">模型配置</button>
      </div>
    </nav>
  </aside>
</template>

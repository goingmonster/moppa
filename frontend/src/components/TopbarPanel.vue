<script setup lang="ts">
defineProps<{
  dataSourceLabel: string
  backendOnline: boolean
  totalEventCount: number
  pendingEventCount: number
  runningTaskCount: number
}>()
</script>

<template>
  <header class="topbar panel">
    <div class="topbar-title">
      <h1>模型预测指挥甲板</h1>
    </div>
    <div class="topbar-meta">
      <div class="status-pills">
        <span class="chip">数据源：{{ dataSourceLabel }}</span>
        <span :class="['chip', backendOnline ? 'chip-online' : 'chip-offline']">后端：{{ backendOnline ? '在线' : '离线' }}</span>
      </div>
      <div class="metric-strip">
        <article class="metric-card">
          <small>事件总量</small>
          <strong>{{ totalEventCount }}</strong>
        </article>
        <article class="metric-card">
          <small>待审核事件</small>
          <strong>{{ pendingEventCount }}</strong>
        </article>
        <article class="metric-card">
          <small>运行中任务</small>
          <strong>{{ runningTaskCount }}</strong>
        </article>
      </div>
    </div>
  </header>
</template>

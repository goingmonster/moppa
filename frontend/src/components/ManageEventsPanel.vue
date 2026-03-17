<script setup lang="ts">
interface EventItem {
  id: string
  codename: string
  title: string
  url: string | null
  theater: string
  summary: string
  tags: string[]
  severity: 'low' | 'medium' | 'high'
  filterStatus: string
  timestamp: string
}

defineProps<{
  eventManagePage: number
  eventManageTotalPages: number
  allEventsOnPageSelected: boolean
  eventReviewProcessing: boolean
  eventManageSearchKeyword: string
  eventManageFilterStatus: string
  eventManageTimeFrom: string
  eventManageTimeTo: string
  eventManageSearchLoading: boolean
  backendOnline: boolean
  manageEventTotal: number
  localFilteredManageEventsLength: number
  skeletonRows: number[]
  hasManageEvents: boolean
  pagedManageEvents: EventItem[]
  selectedEventId: string
  selectedManageEventIds: string[]
  eventManagePageSize: number
  eventManagePageSizeOptions: number[]
  eventManageJumpPage: string
}>()

const emit = defineEmits<{
  (e: 'open-create-event'): void
  (e: 'toggle-select-all'): void
  (e: 'review-events', value: 'passed' | 'filtered'): void
  (e: 'delete-selected-batch'): void
  (e: 'update:search-keyword', value: string): void
  (e: 'update:filter-status', value: string): void
  (e: 'update:time-from', value: string): void
  (e: 'update:time-to', value: string): void
  (e: 'select-event', id: string): void
  (e: 'open-manage-detail', item: EventItem): void
  (e: 'toggle-selection', id: string): void
  (e: 'open-edit', item: EventItem): void
  (e: 'set-page-size', value: number): void
  (e: 'go-page', delta: number): void
  (e: 'update:jump-page', value: string): void
  (e: 'jump-to-page'): void
}>()

const severityLabel: Record<EventItem['severity'], string> = {
  low: '低',
  medium: '中',
  high: '高',
}

function severityBadgeTone(value: EventItem['severity']): string {
  if (value === 'high') {
    return 'badge-error'
  }
  if (value === 'medium') {
    return 'badge-warning'
  }
  return 'badge-info'
}

function eventFilterBadgeTone(status: string): string {
  if (status === 'passed') {
    return 'badge-success'
  }
  if (status === 'matched') {
    return 'badge-info'
  }
  if (status === 'filtered') {
    return 'badge-error'
  }
  if (status === 'pending') {
    return 'badge-warning'
  }
  if (status === 'reviewed') {
    return 'badge-info'
  }
  return 'badge-muted'
}
</script>

<template>
  <main class="manage-grid">
    <article class="panel list-panel">
      <div class="panel-head">
        <h2>事件列表</h2>
        <span>第 {{ eventManagePage }} / {{ eventManageTotalPages }} 页</span>
      </div>
      <div class="action-row manage-toolbar">
        <button class="action-btn" @click="emit('open-create-event')">新增事件</button>
        <button class="action-btn" @click="emit('toggle-select-all')">{{ allEventsOnPageSelected ? '取消全选本页' : '全选本页' }}</button>
        <button class="action-btn compact-btn" :disabled="eventReviewProcessing" @click="emit('review-events', 'passed')">批量通过</button>
        <button class="action-btn danger compact-btn" :disabled="eventReviewProcessing" @click="emit('review-events', 'filtered')">批量拒绝</button>
        <button class="action-btn danger compact-btn" @click="emit('delete-selected-batch')">批量删除所选</button>
        <input
          :value="eventManageSearchKeyword"
          class="toolbar-grow"
          placeholder="搜索事件标题/内容"
          @input="emit('update:search-keyword', ($event.target as HTMLInputElement).value)"
        />
        <select :value="eventManageFilterStatus" @change="emit('update:filter-status', ($event.target as HTMLSelectElement).value)">
          <option value="">全部状态</option>
          <option value="pending">pending</option>
          <option value="passed">passed</option>
          <option value="matched">matched</option>
          <option value="filtered">filtered</option>
          <option value="reviewed">reviewed（passed + filtered）</option>
        </select>
        <input
          :value="eventManageTimeFrom"
          type="datetime-local"
          placeholder="发布时间起"
          @input="emit('update:time-from', ($event.target as HTMLInputElement).value)"
        />
        <input
          :value="eventManageTimeTo"
          type="datetime-local"
          placeholder="发布时间止"
          @input="emit('update:time-to', ($event.target as HTMLInputElement).value)"
        />
        <small class="toolbar-note">{{ eventManageSearchLoading ? '搜索中...' : `匹配 ${backendOnline ? manageEventTotal : localFilteredManageEventsLength} 条` }}</small>
      </div>
      <div v-if="eventManageSearchLoading" class="skeleton-list" aria-hidden="true">
        <article v-for="row in skeletonRows" :key="`event-skeleton-${row}`" class="skeleton-card"></article>
      </div>
      <div v-else-if="!hasManageEvents" class="empty-state">当前筛选下暂无事件</div>
      <ul v-else class="event-list event-list-tall">
        <li
          v-for="eventItem in pagedManageEvents"
          :key="`manage-${eventItem.id}`"
          :class="['event-card', 'with-actions', { active: eventItem.id === selectedEventId }]"
          @click="emit('select-event', eventItem.id); emit('open-manage-detail', eventItem)"
        >
          <div class="row-between">
            <label class="select-row" @click.stop>
              <input type="checkbox" :checked="selectedManageEventIds.includes(eventItem.id)" @change="emit('toggle-selection', eventItem.id)" />
              <span>选择</span>
            </label>
            <strong class="item-title">{{ eventItem.title }}</strong>
            <div class="tag-group">
              <span :class="['badge', severityBadgeTone(eventItem.severity)]">{{ severityLabel[eventItem.severity] }}</span>
              <span :class="['badge', eventFilterBadgeTone(eventItem.filterStatus)]">{{ eventItem.filterStatus }}</span>
            </div>
          </div>
          <p class="item-meta">{{ eventItem.theater }}</p>
          <small class="item-subtle">{{ eventItem.summary }}</small>
          <div v-if="eventItem.tags.length > 0" class="tag-group">
            <span v-for="tag in eventItem.tags" :key="`manage-tag-${eventItem.id}-${tag}`" class="badge">{{ tag }}</span>
          </div>
          <div class="action-row action-right card-actions">
            <button class="action-btn" @click.stop="emit('open-edit', eventItem)">编辑</button>
          </div>
        </li>
      </ul>
      <div class="action-row pagination-row pagination-center">
        <span>每页</span>
        <select :value="eventManagePageSize" @change="emit('set-page-size', Number(($event.target as HTMLSelectElement).value))">
          <option v-for="size in eventManagePageSizeOptions" :key="`event-page-size-${size}`" :value="size">{{ size }}</option>
        </select>
        <button class="action-btn" @click="emit('go-page', -1)">上一页</button>
        <input :value="eventManageJumpPage" class="jump-input" placeholder="页码" @input="emit('update:jump-page', ($event.target as HTMLInputElement).value)" />
        <button class="action-btn" @click="emit('jump-to-page')">跳转</button>
        <button class="action-btn" @click="emit('go-page', 1)">下一页</button>
      </div>
    </article>
  </main>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

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

const props = defineProps<{
  items: EventItem[]
  allLoadedEventsSelected: boolean
  eventReviewProcessing: boolean
  eventManageSearchKeyword: string
  eventManageSourceSystem: string
  eventManageFilterStatus: string
  eventManageTimeFrom: string
  eventManageTimeTo: string
  loading: boolean
  backendOnline: boolean
  matchingTotal: number
  loadedCount: number
  hasMore: boolean
  skeletonRows: number[]
  selectedEventId: string
  selectedManageEventIds: string[]
  sourceSystemOptions: string[]
}>()

const emit = defineEmits<{
  (e: 'open-create-event'): void
  (e: 'toggle-select-all'): void
  (e: 'review-events', value: 'passed' | 'filtered'): void
  (e: 'delete-selected-batch'): void
  (e: 'update:search-keyword', value: string): void
  (e: 'update:source-system', value: string): void
  (e: 'update:filter-status', value: string): void
  (e: 'update:time-from', value: string): void
  (e: 'update:time-to', value: string): void
  (e: 'select-event', id: string): void
  (e: 'open-manage-detail', item: EventItem): void
  (e: 'toggle-selection', id: string): void
  (e: 'open-edit', item: EventItem): void
  (e: 'load-more'): void
}>()

const sentinelRef = ref<HTMLElement | null>(null)
let observer: IntersectionObserver | null = null

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

function setupObserver(): void {
  if (observer || !sentinelRef.value) {
    return
  }
  observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting && props.hasMore && !props.loading) {
          emit('load-more')
        }
      }
    },
    { root: null, threshold: 0.15, rootMargin: '120px 0px' },
  )
  observer.observe(sentinelRef.value)
}

function teardownObserver(): void {
  if (!observer) {
    return
  }
  observer.disconnect()
  observer = null
}

onMounted(() => {
  setupObserver()
})

onBeforeUnmount(() => {
  teardownObserver()
})
</script>

<template>
  <main class="feed-shell question-community-shell manage-events-shell">
    <section class="manage-events-feed" aria-label="事件流">
      <div class="manage-events-feed-head">
        <div class="manage-events-kicker">Community Pulse</div>
        <div class="manage-events-feed-meta">
          <div class="manage-events-feed-meta-copy">
            <strong>事件现场</strong>
          </div>
          <small>{{ loading ? '加载中...' : `匹配 ${matchingTotal} 条，已加载 ${loadedCount} 条` }}</small>
        </div>
      </div>

      <div v-if="loading && items.length === 0" class="skeleton-list" aria-hidden="true">
        <article v-for="row in skeletonRows" :key="`event-skeleton-${row}`" class="skeleton-card"></article>
      </div>
      <div v-else-if="items.length === 0" class="empty-state">当前筛选下暂无事件</div>
      <ul v-else class="event-list manage-events-stream">
        <li
          v-for="eventItem in items"
          :key="`manage-${eventItem.id}`"
          :class="['event-card', 'with-actions', 'manage-event-card', { active: eventItem.id === selectedEventId }]"
          @click="emit('select-event', eventItem.id); emit('open-manage-detail', eventItem)"
        >
          <div class="row-between manage-event-card-head">
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
          <p class="item-meta">来源系统：{{ eventItem.theater }}</p>
          <small class="item-subtle">{{ eventItem.summary }}</small>
          <div v-if="eventItem.tags.length > 0" class="tag-group">
            <span v-for="tag in eventItem.tags" :key="`manage-tag-${eventItem.id}-${tag}`" class="badge">{{ tag }}</span>
          </div>
          <div class="action-row action-right card-actions">
            <button class="action-btn" @click.stop="emit('open-edit', eventItem)">编辑</button>
          </div>
        </li>
      </ul>

      <div ref="sentinelRef" class="stream-sentinel" aria-hidden="true"></div>

      <div class="action-row action-right manage-events-load-row">
        <small v-if="loading" class="item-subtle">正在加载更多事件...</small>
        <small v-else-if="hasMore" class="item-subtle">已加载 {{ loadedCount }} / {{ matchingTotal }} 条，继续下滑可自动加载</small>
        <small v-else class="item-subtle">已加载全部事件</small>
        <button class="action-btn mini-btn" :disabled="loading || !hasMore" @click="emit('load-more')">
          {{ loading ? '加载中...' : hasMore ? '加载更多事件' : '已无更多事件' }}
        </button>
      </div>
    </section>

    <aside class="question-community-side manage-events-side" aria-label="事件管理区">
      <section class="panel participation-filter-panel manage-events-control-panel">
        <div class="panel-head">
          <h2>控制台</h2>
        </div>
        <div class="action-row manage-toolbar manage-events-toolbar-actions">
          <button class="action-btn" @click="emit('open-create-event')">新增事件</button>
          <button class="action-btn" @click="emit('toggle-select-all')">{{ allLoadedEventsSelected ? '取消全选当前已加载' : '全选当前已加载' }}</button>
          <button class="action-btn compact-btn" :disabled="eventReviewProcessing" @click="emit('review-events', 'passed')">批量通过</button>
          <button class="action-btn danger compact-btn" :disabled="eventReviewProcessing" @click="emit('review-events', 'filtered')">批量拒绝</button>
          <button class="action-btn danger compact-btn" @click="emit('delete-selected-batch')">批量删除所选</button>
        </div>
      </section>

      <section class="panel participation-filter-panel manage-events-control-panel">
        <div class="panel-head">
          <h2>筛选条件</h2>
        </div>
        <div class="action-row manage-toolbar manage-events-toolbar-fields">
          <input
            :value="eventManageSearchKeyword"
            class="toolbar-grow"
            placeholder="搜索事件标题/内容"
            @input="emit('update:search-keyword', ($event.target as HTMLInputElement).value)"
          />
          <select :value="eventManageSourceSystem" @change="emit('update:source-system', ($event.target as HTMLSelectElement).value)">
            <option value="">全部数据源</option>
            <option v-for="sourceSystem in sourceSystemOptions" :key="`event-source-${sourceSystem}`" :value="sourceSystem">{{ sourceSystem }}</option>
          </select>
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
          <small class="toolbar-note">{{ loading ? '加载中...' : `匹配 ${matchingTotal} 条，已加载 ${loadedCount} 条` }}</small>
        </div>
      </section>
    </aside>
  </main>
</template>

<style scoped>
.manage-events-shell {
  align-items: start;
}

.manage-events-feed {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  min-width: 0;
  position: relative;
}

.manage-events-feed-head {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 0.25rem 0 1rem;
}

.manage-events-kicker {
  align-self: start;
  padding: 0.3rem 0.7rem;
  border: 1px solid color-mix(in srgb, var(--line-soft) 75%, transparent);
  border-radius: 999px;
  background: color-mix(in srgb, var(--surface-1) 72%, transparent);
  color: var(--text-subtle);
  font-size: 0.72rem;
  letter-spacing: 0.24em;
  text-transform: uppercase;
}

.manage-events-title {
  padding: 0;
}

.manage-events-title :deep(h2) {
  font-size: clamp(1.8rem, 3vw, 2.45rem);
}

.manage-events-feed-meta {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.9rem 1rem 1rem;
  border-bottom: 1px solid var(--line-soft);
  border-top: 1px solid color-mix(in srgb, var(--line-soft) 55%, transparent);
  background:
    radial-gradient(circle at top left, color-mix(in srgb, var(--brand) 14%, transparent), transparent 45%),
    color-mix(in srgb, var(--surface-1) 76%, transparent);
  border-radius: 18px;
}

.manage-events-feed-meta strong {
  font-size: 0.82rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--text-subtle);
}

.manage-events-feed-meta-copy {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.manage-events-feed-meta-copy p {
  margin: 0;
  max-width: 32rem;
  color: var(--text-subtle);
  line-height: 1.55;
}

.manage-events-feed-meta small {
  color: var(--text-subtle);
  white-space: nowrap;
}

.manage-events-stream {
  max-height: none;
  overflow: visible;
  gap: 1rem;
}

.manage-event-card {
  border-radius: 14px;
  border-color: color-mix(in srgb, var(--line-soft) 82%, transparent);
  background:
    linear-gradient(180deg, color-mix(in srgb, var(--surface-1) 92%, transparent), color-mix(in srgb, var(--surface-2) 88%, transparent));
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.06);
  transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
}

.manage-event-card-head {
  align-items: start;
}

.manage-event-card:hover {
  transform: translateY(-2px);
  border-color: color-mix(in srgb, var(--brand) 30%, var(--line-soft));
  box-shadow: 0 24px 50px rgba(15, 23, 42, 0.1);
}

.manage-event-card .item-title {
  font-size: 1.02rem;
  line-height: 1.45;
}

.manage-event-card .item-meta {
  margin-top: 0.25rem;
}

.manage-event-card .item-subtle {
  line-height: 1.6;
}

.manage-events-load-row {
  padding-top: 0.35rem;
}

.manage-events-side {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.manage-events-control-panel {
  width: 100%;
  border-radius: 16px;
}

.manage-events-side-note {
  margin: 0;
  color: var(--text-subtle);
  line-height: 1.55;
}

.manage-events-toolbar-actions,
.manage-events-toolbar-fields {
  flex-direction: column;
  align-items: stretch;
}

.manage-events-toolbar-actions .action-btn,
.manage-events-toolbar-fields input,
.manage-events-toolbar-fields select {
  width: 100%;
}

.manage-events-toolbar-fields .toolbar-grow {
  flex: 1 1 auto;
  min-width: 0;
}

@media (max-width: 900px) {
  .manage-events-feed-meta {
    align-items: start;
    flex-direction: column;
  }

  .manage-events-feed-meta small {
    white-space: normal;
  }
}
</style>

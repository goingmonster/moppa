<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

interface QuestionItem {
  id: string
  eventIds: string[]
  level: 'L1' | 'L2' | 'L3' | 'L4'
  title: string
  answerSpace: string
  hypothesis: string
  deadline: string
  status: 'collecting' | 'locked' | 'resolved'
  groundTruth: string
}

interface EventOption {
  id: string
  title: string
}

const props = defineProps<{
  items: QuestionItem[]
  loading: boolean
  hasMore: boolean
  backendOnline: boolean
  allKnownEvents: EventOption[]
}>()

const emit = defineEmits<{
  (e: 'load-more'): void
  (e: 'open-question', item: QuestionItem): void
}>()

const sentinelRef = ref<HTMLElement | null>(null)
let observer: IntersectionObserver | null = null

const statusLabel: Record<QuestionItem['status'], string> = {
  collecting: '收集中',
  locked: '已封存',
  resolved: '已解析',
}

function statusTone(status: QuestionItem['status']): string {
  if (status === 'resolved') {
    return 'badge-success'
  }
  if (status === 'locked') {
    return 'badge-info'
  }
  return 'badge-warning'
}

function formatDeadline(value: string): string {
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return value
  }
  return parsed.toLocaleString('zh-CN', { hour12: false })
}

const eventTitleMap = computed(() => {
  const map = new Map<string, string>()
  for (const item of props.allKnownEvents) {
    map.set(item.id, item.title)
  }
  return map
})

function eventLabel(ids: string[]): string {
  const labels = ids
    .map((id) => eventTitleMap.value.get(id))
    .filter((title): title is string => Boolean(title))
  return labels.length > 0 ? labels.join('、') : '未关联事件'
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
  <main class="feed-shell">
    <article class="panel feed-panel">
      <div class="panel-head">
        <h2>问题社区</h2>
        <span>自动加载，每次 10 条</span>
      </div>
      <p class="item-subtle">
        {{ backendOnline ? '数据源：后端实时问题流' : '数据源：离线本地问题流' }}
      </p>

      <div v-if="items.length === 0 && !loading" class="empty-state">暂无可展示问题</div>

      <ul v-else class="question-stream-list">
        <li
          v-for="question in items"
          :key="`stream-${question.id}`"
          class="question-stream-card"
          @click="emit('open-question', question)"
        >
          <div class="stream-head">
            <div class="stream-avatar">Q</div>
            <div>
              <strong>MOPPA Question Desk</strong>
              <p class="item-subtle">@moppa-question</p>
            </div>
          </div>
          <p class="item-title">{{ question.title }}</p>
          <p class="item-meta"><strong>答案范围：</strong>{{ question.answerSpace || '未设置' }}</p>
          <p class="item-meta"><strong>关联事件：</strong>{{ eventLabel(question.eventIds) }}</p>
          <div class="tag-group stream-tags">
            <span class="badge">{{ question.level }}</span>
            <span :class="['badge', statusTone(question.status)]">{{ statusLabel[question.status] }}</span>
            <span class="badge">截止：{{ formatDeadline(question.deadline) }}</span>
          </div>
        </li>
      </ul>

      <div ref="sentinelRef" class="stream-sentinel" aria-hidden="true"></div>

      <div class="action-row action-right">
        <small v-if="loading" class="item-subtle">加载中...</small>
        <small v-else-if="!hasMore" class="item-subtle">已加载全部问题</small>
        <button class="action-btn mini-btn" :disabled="loading || !hasMore" @click="emit('load-more')">
          加载下一批
        </button>
      </div>
    </article>
  </main>
</template>

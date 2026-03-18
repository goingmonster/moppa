<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

interface QuestionItem {
  id: string
  eventIds: string[]
  level: 'L1' | 'L2' | 'L3' | 'L4'
  title: string
  matchScore: number | null
  eventDomain: string
  eventType: string
  area: string
  inputType: string
  background: string
  answerSpace: string
  hypothesis: string
  deadline: string
  status: 'collecting' | 'locked' | 'resolved'
  groundTruth: string
  deleteReason: string
  deletedAt: string
}

interface EventOption {
  id: string
  title: string
}

interface QuestionInteractionCount {
  predictionCount: number
  commentCount: number
}

interface QuestionParticipationSummary {
  hasPrediction: boolean
  myCommentCount: number
}

const props = defineProps<{
  items: QuestionItem[]
  interactionCounts: Record<string, QuestionInteractionCount>
  participation: Record<string, QuestionParticipationSummary>
  loading: boolean
  hasMore: boolean
  backendOnline: boolean
  allKnownEvents: EventOption[]
  searchKeyword: string
  filterEventDomain: string
  filterEventType: string
  filterDeadlineFrom: string
  filterDeadlineTo: string
  filterStatus: string
  filterLevel: string
  loadedCount: number
  filteredCount: number
  filtersApplied: boolean
}>()

const emit = defineEmits<{
  (e: 'load-more'): void
  (e: 'open-question', item: QuestionItem): void
  (e: 'update:search-keyword', value: string): void
  (e: 'update:filter-event-domain', value: string): void
  (e: 'update:filter-event-type', value: string): void
  (e: 'update:filter-deadline-from', value: string): void
  (e: 'update:filter-deadline-to', value: string): void
  (e: 'update:filter-status', value: string): void
  (e: 'update:filter-level', value: string): void
  (e: 'clear-filters'): void
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
  if (ids.length === 0) {
    return '未关联事件'
  }
  const labels = ids
    .map((id) => eventTitleMap.value.get(id))
    .filter((title): title is string => Boolean(title))
  if (labels.length === ids.length) {
    return labels.join('、')
  }
  if (labels.length > 0) {
    return `${labels.join('、')}（另有 ${ids.length - labels.length} 个事件待加载）`
  }
  return `已关联 ${ids.length} 个事件（名称加载中）`
}

function interactionCount(questionId: string): QuestionInteractionCount {
  return props.interactionCounts[questionId] ?? { predictionCount: 0, commentCount: 0 }
}

const participatedItems = computed(() =>
  props.items.filter((item) => {
    const summary = props.participation[item.id]
    if (!summary) {
      return false
    }
    return summary.hasPrediction || summary.myCommentCount > 0
  }),
)

const participationPage = ref(1)
const participationPageSize = 3

const participationTotalPages = computed(() =>
  Math.max(1, Math.ceil(participatedItems.value.length / participationPageSize)),
)

const pagedParticipatedItems = computed(() => {
  const start = (participationPage.value - 1) * participationPageSize
  return participatedItems.value.slice(start, start + participationPageSize)
})

watch(participatedItems, () => {
  const totalPages = participationTotalPages.value
  if (participationPage.value > totalPages) {
    participationPage.value = totalPages
  }
  if (participationPage.value < 1) {
    participationPage.value = 1
  }
})

function goParticipationPage(offset: number): void {
  const next = participationPage.value + offset
  if (next < 1 || next > participationTotalPages.value) {
    return
  }
  participationPage.value = next
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
  <main class="feed-shell question-community-shell">
    <article class="panel feed-panel">
      <div class="panel-head">
        <h2>问题社区</h2>
        <span>自动加载，每次 10 条</span>
      </div>
      <p class="item-subtle">
        {{ backendOnline ? '数据源：后端实时问题流' : '数据源：离线本地问题流' }}
      </p>

      <div v-if="items.length === 0 && !loading && (filtersApplied || !hasMore)" class="empty-state">
        {{ filtersApplied ? '当前筛选条件下暂无匹配问题，继续下滑可加载更多候选数据' : '暂无可展示问题' }}
      </div>

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
          <p class="item-meta"><strong>事件域：</strong>{{ question.eventDomain || '-' }} ｜ <strong>事件类型：</strong>{{ question.eventType || '-' }}</p>
          <p class="item-meta"><strong>区域：</strong>{{ question.area || '-' }} ｜ <strong>输入类型：</strong>{{ question.inputType || '-' }}</p>
          <p class="item-meta"><strong>匹配分：</strong>{{ question.matchScore ?? '-' }}</p>
          <p class="item-meta"><strong>答案范围：</strong>{{ question.answerSpace || '未设置' }}</p>
          <p class="item-meta"><strong>关联事件：</strong>{{ eventLabel(question.eventIds) }}</p>
          <div class="action-row stream-engagement-row">
            <span class="chip">预测 {{ interactionCount(question.id).predictionCount }}</span>
            <span class="chip">评论 {{ interactionCount(question.id).commentCount }}</span>
          </div>
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

    <aside class="question-community-side">
      <section class="panel participation-panel">
        <div class="panel-head">
          <h2>我的参与</h2>
          <span>预测/评论</span>
        </div>
        <p v-if="participatedItems.length === 0" class="item-subtle">你还没有参与当前列表中的问题</p>
        <div v-else class="participation-list participation-scroll-box">
          <button
            v-for="item in pagedParticipatedItems"
            :key="`participation-${item.id}`"
            type="button"
            class="participation-item"
            @click="emit('open-question', item)"
          >
            <strong>{{ item.title }}</strong>
            <span class="item-subtle">
              {{ participation[item.id]?.hasPrediction ? '已预测' : '未预测' }}
              · 我评论 {{ participation[item.id]?.myCommentCount ?? 0 }} 条
            </span>
          </button>
        </div>
        <div v-if="participatedItems.length > participationPageSize" class="action-row mini-pagination participation-pagination">
          <button class="action-btn mini-btn" :disabled="participationPage <= 1" @click="goParticipationPage(-1)">上一页</button>
          <span>第 {{ participationPage }} / {{ participationTotalPages }} 页</span>
          <button
            class="action-btn mini-btn"
            :disabled="participationPage >= participationTotalPages"
            @click="goParticipationPage(1)"
          >
            下一页
          </button>
        </div>
      </section>

      <section class="panel participation-filter-panel">
        <div class="panel-head">
          <h2>搜索与过滤</h2>
          <span>独立筛选区</span>
        </div>
        <div class="question-feed-filter-scroll-box">
          <div class="action-row manage-toolbar question-feed-filter-bar">
            <input
              :value="searchKeyword"
              class="toolbar-grow"
              placeholder="模糊搜索：标题/背景/答案范围/假设/真实结果"
              @input="emit('update:search-keyword', ($event.target as HTMLInputElement).value)"
            />
            <input
              :value="filterEventDomain"
              placeholder="事件域（模糊）"
              @input="emit('update:filter-event-domain', ($event.target as HTMLInputElement).value)"
            />
            <input
              :value="filterEventType"
              placeholder="事件类型（模糊）"
              @input="emit('update:filter-event-type', ($event.target as HTMLInputElement).value)"
            />
            <input
              :value="filterDeadlineFrom"
              type="datetime-local"
              placeholder="截止时间起"
              @input="emit('update:filter-deadline-from', ($event.target as HTMLInputElement).value)"
            />
            <input
              :value="filterDeadlineTo"
              type="datetime-local"
              placeholder="截止时间止"
              @input="emit('update:filter-deadline-to', ($event.target as HTMLInputElement).value)"
            />
            <select
              :value="filterStatus"
              @change="emit('update:filter-status', ($event.target as HTMLSelectElement).value)"
            >
              <option value="">全部状态</option>
              <option value="collecting">收集中</option>
              <option value="locked">已封存</option>
              <option value="resolved">已解析</option>
            </select>
            <select
              :value="filterLevel"
              @change="emit('update:filter-level', ($event.target as HTMLSelectElement).value)"
            >
              <option value="">全部等级</option>
              <option value="L1">L1</option>
              <option value="L2">L2</option>
              <option value="L3">L3</option>
              <option value="L4">L4</option>
            </select>
            <button class="action-btn" :disabled="!filtersApplied" @click="emit('clear-filters')">清空筛选</button>
            <small class="toolbar-note">当前匹配 {{ filteredCount }} 条（已加载 {{ loadedCount }} 条）</small>
          </div>
        </div>
      </section>
    </aside>
  </main>
</template>

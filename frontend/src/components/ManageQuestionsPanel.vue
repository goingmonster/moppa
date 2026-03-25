<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

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
  status: 'draft' | 'pending_review' | 'published' | 'expired' | 'matched' | 'closed'
  hypothesis: string
  deadline: string
  groundTruth: string
  deleteReason: string
  deletedAt: string
}

interface EventOption {
  id: string
  title: string
}

const props = defineProps<{
  allLoadedManageQuestionsSelected: boolean
  questionManageSearchKeyword: string
  questionManageFilterEventDomain: string
  questionManageFilterEventType: string
  questionManageFilterDeadlineFrom: string
  questionManageFilterDeadlineTo: string
  questionManageFilterStatus: string
  questionManageFilterLevel: string
  questionManageDeletedMode: 'active_only' | 'with_deleted' | 'deleted_only'
  questionManageFiltersApplied: boolean
  questionManageLoading: boolean
  backendOnline: boolean
  questionManageTotal: number
  skeletonRows: number[]
  loadedManageQuestions: QuestionItem[]
  selectedQuestionId: string
  selectedManageQuestionIds: string[]
  questionManageHasMore: boolean
  allKnownEvents: EventOption[]
}>()

const emit = defineEmits<{
  (e: 'open-create-question'): void
  (e: 'toggle-select-all'): void
  (e: 'delete-selected-batch'): void
  (e: 'update:search-keyword', value: string): void
  (e: 'update:filter-event-domain', value: string): void
  (e: 'update:filter-event-type', value: string): void
  (e: 'update:filter-deadline-from', value: string): void
  (e: 'update:filter-deadline-to', value: string): void
  (e: 'update:filter-status', value: string): void
  (e: 'update:filter-level', value: string): void
  (e: 'update:deleted-mode', value: 'active_only' | 'with_deleted' | 'deleted_only'): void
  (e: 'clear-filters'): void
  (e: 'select-question', id: string): void
  (e: 'open-manage-detail', item: QuestionItem): void
  (e: 'toggle-selection', id: string): void
  (e: 'open-edit', item: QuestionItem): void
  (e: 'load-more'): void
}>()

const manageToolbarCollapsed = ref(true)
const sentinelRef = ref<HTMLElement | null>(null)
let observer: IntersectionObserver | null = null

const statusLabel: Record<QuestionItem['status'], string> = {
  draft: '收集中',
  pending_review: '待评审',
  published: '已发布',
  expired: '已过期',
  matched: '已匹配',
  closed: '已解析',
}

function questionStatusBadgeTone(status: QuestionItem['status']): string {
  if (status === 'closed') {
    return 'badge-success'
  }
  if (status === 'expired') {
    return 'badge-error'
  }
  if (status === 'pending_review' || status === 'published' || status === 'matched') {
    return 'badge-info'
  }
  return 'badge-warning'
}

function eventLabel(eventIds: string[], allKnownEvents: EventOption[]): string {
  if (eventIds.length === 0) {
    return '未关联事件'
  }
  const labels = eventIds
    .map((eventId) => allKnownEvents.find((eventItem) => eventItem.id === eventId)?.title)
    .filter((title): title is string => Boolean(title))
  if (labels.length === eventIds.length) {
    return labels.join('、')
  }
  if (labels.length > 0) {
    return `${labels.join('、')}（另有 ${eventIds.length - labels.length} 个事件待加载）`
  }
  return `已关联 ${eventIds.length} 个事件（名称加载中）`
}

const selectionToggleLabel = computed(() =>
  props.allLoadedManageQuestionsSelected ? '取消全选当前已加载' : '全选当前已加载',
)

const loadedQuestionCount = computed(() => props.loadedManageQuestions.length)

const toolbarMatchLabel = computed(() => {
  if (props.questionManageLoading) {
    return '加载中...'
  }
  if (props.backendOnline) {
    return `已加载 ${loadedQuestionCount.value} / 共 ${props.questionManageTotal} 条`
  }
  return `已加载 ${loadedQuestionCount.value} / 匹配 ${props.questionManageTotal} 条`
})

const emptyStateLabel = computed(() => {
  if (!props.questionManageFiltersApplied) {
    return '暂无可展示问题'
  }
  if (props.questionManageHasMore) {
    return '当前已加载结果里暂无匹配问题，继续下滑可加载更多候选数据'
  }
  return '当前筛选条件下暂无问题'
})

const footerStatusLabel = computed(() => {
  if (props.questionManageLoading) {
    return '正在加载更多问题...'
  }
  if (!props.questionManageHasMore) {
    return `已加载全部问题（${loadedQuestionCount.value} 条）`
  }
  if (props.loadedManageQuestions.length === 0) {
    return '向下滚动以加载问题'
  }
  return `已加载 ${loadedQuestionCount.value} 条，继续下滑可自动加载`
})

function setupObserver(): void {
  if (observer || !sentinelRef.value) {
    return
  }
  observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting && props.questionManageHasMore && !props.questionManageLoading) {
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
  <main class="feed-shell question-community-shell manage-questions-shell">
    <section class="manage-questions-feed" aria-label="问题流">
      <div class="manage-questions-feed-head">
        <div class="manage-questions-feed-meta">
          <strong>问题现场</strong>
          <small>{{ toolbarMatchLabel }}</small>
        </div>
      </div>

      <div v-if="questionManageLoading && loadedManageQuestions.length === 0" class="skeleton-list" aria-hidden="true">
        <article v-for="row in skeletonRows" :key="`question-skeleton-${row}`" class="skeleton-card"></article>
      </div>
      <div
        v-else-if="loadedManageQuestions.length === 0 && !questionManageLoading && (questionManageFiltersApplied || !questionManageHasMore)"
        class="empty-state"
      >
        {{ emptyStateLabel }}
      </div>
      <ul v-else-if="loadedManageQuestions.length > 0" class="event-list manage-questions-stream">
        <li
          v-for="question in loadedManageQuestions"
          :key="`manage-${question.id}`"
          :class="['question-card', 'with-actions', 'manage-question-card', { active: question.id === selectedQuestionId }]"
          @click="emit('select-question', question.id); emit('open-manage-detail', question)"
        >
          <div class="row-between">
            <label class="select-row" @click.stop>
              <input
                type="checkbox"
                :checked="selectedManageQuestionIds.includes(question.id)"
                :disabled="Boolean(question.deletedAt)"
                @change="emit('toggle-selection', question.id)"
              />
              <span>选择</span>
            </label>
            <div class="tag-group">
              <span class="badge">{{ question.level }}</span>
              <span :class="['badge', questionStatusBadgeTone(question.status)]">{{ statusLabel[question.status] }}</span>
              <span v-if="question.deletedAt" class="badge badge-danger">已删除</span>
            </div>
          </div>
          <p class="item-title">{{ question.title }}</p>
          <small class="item-meta">
            关联事件：
            {{ eventLabel(question.eventIds, allKnownEvents) }}
          </small>
          <small class="item-meta">事件域：{{ question.eventDomain || '-' }} ｜ 事件类型：{{ question.eventType || '-' }} ｜ 区域：{{ question.area || '-' }}</small>
          <small class="item-meta">输入类型：{{ question.inputType || '-' }} ｜ 匹配分：{{ question.matchScore ?? '-' }}</small>
          <small v-if="question.deletedAt" class="item-meta">删除原因：{{ question.deleteReason || '未填写' }}</small>
          <div class="action-row action-right card-actions">
            <button class="action-btn" @click.stop="emit('open-edit', question)">编辑</button>
          </div>
        </li>
      </ul>
      <div ref="sentinelRef" class="stream-sentinel" aria-hidden="true"></div>
      <div class="action-row action-right manage-questions-load-row">
          <small class="item-subtle">{{ footerStatusLabel }}</small>
          <button class="action-btn mini-btn" :disabled="questionManageLoading || !questionManageHasMore" @click="emit('load-more')">
          {{ questionManageLoading ? '加载中...' : questionManageHasMore ? '加载更多问题' : '已无更多问题' }}
          </button>
      </div>
    </section>

    <aside class="question-community-side manage-questions-side" aria-label="问题管理区">
      <section class="panel participation-filter-panel manage-questions-control-panel compact-control-panel">
        <div class="panel-head toolbar-head">
          <h2>操作与筛选</h2>
          <button class="action-btn mini-btn" @click="manageToolbarCollapsed = !manageToolbarCollapsed">
            {{ manageToolbarCollapsed ? '展开' : '折叠' }}
          </button>
        </div>
        <p v-if="manageToolbarCollapsed" class="item-subtle">已折叠（点击展开查看操作与筛选）</p>
        <template v-else>
          <div class="manage-questions-side-section">
            <div class="manage-questions-side-section-head">
              <strong>快捷操作</strong>
            </div>
          <div class="manage-question-toolbar-actions">
            <button class="action-btn" @click="emit('open-create-question')">新增问题</button>
            <button class="action-btn" @click="emit('toggle-select-all')">{{ selectionToggleLabel }}</button>
            <button class="action-btn danger" @click="emit('delete-selected-batch')">批量删除所选</button>
            <button class="action-btn" :disabled="!questionManageFiltersApplied" @click="emit('clear-filters')">清空筛选</button>
          </div>
          </div>
          <div class="manage-questions-side-section">
            <div class="manage-questions-side-section-head">
              <strong>筛选条件</strong>
            </div>
            <div class="manage-question-filter-row manage-question-filter-row-wide">
            <input
              :value="questionManageSearchKeyword"
              placeholder="模糊搜索：标题/背景/事件域/删除原因"
              @input="emit('update:search-keyword', ($event.target as HTMLInputElement).value)"
            />
            <input
              :value="questionManageFilterEventDomain"
              placeholder="事件域（模糊）"
              @input="emit('update:filter-event-domain', ($event.target as HTMLInputElement).value)"
            />
            <input
              :value="questionManageFilterEventType"
              placeholder="事件类型（模糊）"
              @input="emit('update:filter-event-type', ($event.target as HTMLInputElement).value)"
            />
            <select
              :value="questionManageFilterStatus"
              @change="emit('update:filter-status', ($event.target as HTMLSelectElement).value)"
            >
              <option value="">全部状态</option>
              <option value="draft">收集中</option>
              <option value="pending_review">待评审</option>
              <option value="published">已发布</option>
              <option value="expired">已过期</option>
              <option value="matched">已匹配</option>
              <option value="closed">已解析</option>
            </select>
            </div>
            <div class="manage-question-filter-row manage-question-filter-row-wide">
            <input
              :value="questionManageFilterDeadlineFrom"
              type="datetime-local"
              placeholder="创建时间起"
              @input="emit('update:filter-deadline-from', ($event.target as HTMLInputElement).value)"
            />
            <input
              :value="questionManageFilterDeadlineTo"
              type="datetime-local"
              placeholder="创建时间止"
              @input="emit('update:filter-deadline-to', ($event.target as HTMLInputElement).value)"
            />
            <select
              :value="questionManageFilterLevel"
              @change="emit('update:filter-level', ($event.target as HTMLSelectElement).value)"
            >
              <option value="">全部等级</option>
              <option value="L1">L1</option>
              <option value="L2">L2</option>
              <option value="L3">L3</option>
              <option value="L4">L4</option>
            </select>
            <select
              :value="questionManageDeletedMode"
              @change="emit('update:deleted-mode', ($event.target as HTMLSelectElement).value as 'active_only' | 'with_deleted' | 'deleted_only')"
            >
              <option value="active_only">仅未删除</option>
              <option value="with_deleted">包含已删除</option>
              <option value="deleted_only">仅已删除</option>
            </select>
            </div>
          </div>
        </template>
      </section>
    </aside>
  </main>
</template>

<style scoped>
.manage-questions-shell {
  align-items: start;
}

.manage-questions-feed {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  min-width: 0;
}

.manage-questions-feed-head {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.manage-questions-title {
  padding: 0;
}

.manage-questions-feed-meta {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.75rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--line-soft);
}

.manage-questions-feed-meta strong {
  font-size: 0.82rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--text-subtle);
}

.manage-questions-feed-meta small {
  color: var(--text-subtle);
}

.manage-questions-stream {
  max-height: none;
  overflow: visible;
  gap: 0.9rem;
}

.manage-question-card {
  border-radius: 14px;
  border-color: color-mix(in srgb, var(--line-soft) 82%, transparent);
  background: color-mix(in srgb, var(--surface-1) 82%, transparent);
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
}

.manage-questions-load-row {
  padding-top: 0.35rem;
}

.manage-questions-side {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.manage-questions-control-panel {
  width: 100%;
  display: grid;
  gap: 0.95rem;
}

.manage-questions-side-section {
  display: grid;
  gap: 0.7rem;
}

.manage-questions-side-section-head {
  display: grid;
  gap: 0.24rem;
  padding-bottom: 0.55rem;
  border-bottom: 1px solid color-mix(in srgb, var(--line-soft) 75%, transparent);
}

.manage-questions-side-section-head strong {
  font-size: 0.85rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text);
}

.manage-questions-side-section-head small {
  color: var(--text-subtle);
  line-height: 1.5;
}

.manage-question-toolbar-actions {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.65rem;
}

.manage-question-filter-row-wide {
  grid-template-columns: 1fr;
  gap: 0.65rem;
}

.manage-question-filter-row-wide input,
.manage-question-filter-row-wide select {
  min-height: 38px;
}

.manage-questions-control-panel :deep(.toolbar-head) {
  margin-bottom: 0;
}

@media (max-width: 900px) {
  .manage-questions-feed-meta {
    align-items: start;
    flex-direction: column;
  }

  .manage-question-toolbar-actions {
    grid-template-columns: 1fr;
  }
}
</style>

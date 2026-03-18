<script setup lang="ts">
import { ref } from 'vue'

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
  status: 'collecting' | 'locked' | 'resolved'
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

defineProps<{
  questionManagePage: number
  questionManageTotalPages: number
  allQuestionsOnPageSelected: boolean
  questionManageSearchKeyword: string
  questionManageFilterEventDomain: string
  questionManageFilterEventType: string
  questionManageFilterDeadlineFrom: string
  questionManageFilterDeadlineTo: string
  questionManageFilterStatus: string
  questionManageFilterLevel: string
  questionManageDeletedMode: 'active_only' | 'with_deleted' | 'deleted_only'
  questionManageFiltersApplied: boolean
  questionManageSearchLoading: boolean
  backendOnline: boolean
  questionManageTotal: number
  localFilteredManageQuestionsLength: number
  skeletonRows: number[]
  hasManageQuestions: boolean
  pagedManageQuestions: QuestionItem[]
  selectedQuestionId: string
  selectedManageQuestionIds: string[]
  questionManagePageSize: number
  questionManagePageSizeOptions: number[]
  questionManageJumpPage: string
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
  (e: 'set-page-size', value: number): void
  (e: 'go-page', delta: number): void
  (e: 'update:jump-page', value: string): void
  (e: 'jump-to-page'): void
}>()

const manageToolbarCollapsed = ref(true)

const statusLabel: Record<QuestionItem['status'], string> = {
  collecting: '收集中',
  locked: '已封存 / 待真实结果',
  resolved: '已解析',
}

function questionStatusBadgeTone(status: QuestionItem['status']): string {
  if (status === 'resolved') {
    return 'badge-success'
  }
  if (status === 'locked') {
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
</script>

<template>
  <main class="manage-grid">
    <article class="panel list-panel manage-question-list-panel">
      <div class="panel-head">
        <h2>问题列表</h2>
        <span>第 {{ questionManagePage }} / {{ questionManageTotalPages }} 页</span>
      </div>
      <section class="manage-question-toolbar-top compact-control-panel">
        <div class="panel-head toolbar-head">
          <h2>操作与筛选</h2>
          <button class="action-btn mini-btn" @click="manageToolbarCollapsed = !manageToolbarCollapsed">
            {{ manageToolbarCollapsed ? '展开' : '折叠' }}
          </button>
        </div>
        <p v-if="manageToolbarCollapsed" class="item-subtle">已折叠（点击展开查看操作与筛选）</p>
        <template v-else>
          <div class="manage-question-toolbar-actions">
            <button class="action-btn" @click="emit('open-create-question')">新增问题</button>
            <button class="action-btn" @click="emit('toggle-select-all')">{{ allQuestionsOnPageSelected ? '取消全选本页' : '全选本页' }}</button>
            <button class="action-btn danger" @click="emit('delete-selected-batch')">批量删除所选</button>
            <button class="action-btn" :disabled="!questionManageFiltersApplied" @click="emit('clear-filters')">清空筛选</button>
          </div>
          <div class="manage-question-filter-row">
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
              <option value="collecting">收集中</option>
              <option value="locked">已封存</option>
              <option value="resolved">已解析</option>
            </select>
          </div>
          <div class="manage-question-filter-row">
            <input
              :value="questionManageFilterDeadlineFrom"
              type="datetime-local"
              @input="emit('update:filter-deadline-from', ($event.target as HTMLInputElement).value)"
            />
            <input
              :value="questionManageFilterDeadlineTo"
              type="datetime-local"
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
          <small class="toolbar-note">{{ questionManageSearchLoading ? '搜索中...' : `匹配 ${backendOnline ? questionManageTotal : localFilteredManageQuestionsLength} 条` }}</small>
        </template>
      </section>
      <div v-if="questionManageSearchLoading" class="skeleton-list" aria-hidden="true">
        <article v-for="row in skeletonRows" :key="`question-skeleton-${row}`" class="skeleton-card"></article>
      </div>
      <div v-else-if="!hasManageQuestions" class="empty-state">当前筛选下暂无问题</div>
      <ul v-else class="event-list">
        <li
          v-for="question in pagedManageQuestions"
          :key="`manage-${question.id}`"
          :class="['question-card', 'with-actions', { active: question.id === selectedQuestionId }]"
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
      <div class="action-row pagination-row pagination-center">
        <span>每页</span>
        <select :value="questionManagePageSize" @change="emit('set-page-size', Number(($event.target as HTMLSelectElement).value))">
          <option v-for="size in questionManagePageSizeOptions" :key="`question-page-size-${size}`" :value="size">{{ size }}</option>
        </select>
        <button class="action-btn" @click="emit('go-page', -1)">上一页</button>
        <input :value="questionManageJumpPage" class="jump-input" placeholder="页码" @input="emit('update:jump-page', ($event.target as HTMLInputElement).value)" />
        <button class="action-btn" @click="emit('jump-to-page')">跳转</button>
        <button class="action-btn" @click="emit('go-page', 1)">下一页</button>
      </div>
    </article>
  </main>
</template>

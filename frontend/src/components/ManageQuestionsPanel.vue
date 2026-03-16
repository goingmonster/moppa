<script setup lang="ts">
interface QuestionItem {
  id: string
  eventIds: string[]
  level: 'L1' | 'L2' | 'L3' | 'L4'
  title: string
  answerSpace: string
  status: 'collecting' | 'locked' | 'resolved'
  hypothesis: string
  deadline: string
  groundTruth: string
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
  (e: 'select-question', id: string): void
  (e: 'open-manage-detail', item: QuestionItem): void
  (e: 'toggle-selection', id: string): void
  (e: 'open-edit', item: QuestionItem): void
  (e: 'set-page-size', value: number): void
  (e: 'go-page', delta: number): void
  (e: 'update:jump-page', value: string): void
  (e: 'jump-to-page'): void
}>()

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
</script>

<template>
  <main class="manage-grid">
    <article class="panel list-panel">
      <div class="panel-head">
        <h2>问题列表</h2>
        <span>第 {{ questionManagePage }} / {{ questionManageTotalPages }} 页</span>
      </div>
      <div class="action-row manage-toolbar">
        <button class="action-btn" @click="emit('open-create-question')">新增问题</button>
        <button class="action-btn" @click="emit('toggle-select-all')">{{ allQuestionsOnPageSelected ? '取消全选本页' : '全选本页' }}</button>
        <button class="action-btn danger" @click="emit('delete-selected-batch')">批量删除所选</button>
        <input
          :value="questionManageSearchKeyword"
          class="toolbar-grow"
          placeholder="搜索问题标题"
          @input="emit('update:search-keyword', ($event.target as HTMLInputElement).value)"
        />
        <small class="toolbar-note">{{ questionManageSearchLoading ? '搜索中...' : `匹配 ${backendOnline ? questionManageTotal : localFilteredManageQuestionsLength} 条` }}</small>
      </div>
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
              <input type="checkbox" :checked="selectedManageQuestionIds.includes(question.id)" @change="emit('toggle-selection', question.id)" />
              <span>选择</span>
            </label>
            <div class="tag-group">
              <span class="badge">{{ question.level }}</span>
              <span :class="['badge', questionStatusBadgeTone(question.status)]">{{ statusLabel[question.status] }}</span>
            </div>
          </div>
          <p class="item-title">{{ question.title }}</p>
          <small class="item-meta">
            关联事件：
            {{
              question.eventIds
                .map((eventId) => allKnownEvents.find((eventItem) => eventItem.id === eventId)?.title)
                .filter((title): title is string => Boolean(title))
                .join('、') || '未匹配事件'
            }}
          </small>
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

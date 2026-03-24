<script setup lang="ts">
interface TaskItem {
  id: string
  taskType: string
  idempotencyKey: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'dead_letter'
  attemptCount: number
  traceId: string
}

defineProps<{
  tavilyIngestProcessing: boolean
  autoReviewProcessing: boolean
  autoQuestionProcessing: boolean
  locationAnalysisProcessing: boolean
  allTasksOnPageSelected: boolean
  hasTasks: boolean
  tasks: TaskItem[]
  selectedTaskId: string
  selectedManageTaskIds: string[]
  taskManagePageSize: number
  taskManagePageSizeOptions: number[]
  taskManageJumpPage: string
}>()

const emit = defineEmits<{
  (e: 'open-trigger-pull'): void
  (e: 'trigger-tavily-ingest'): void
  (e: 'trigger-auto-review'): void
  (e: 'trigger-auto-question'): void
  (e: 'trigger-location-analysis'): void
  (e: 'open-create-task'): void
  (e: 'toggle-select-all'): void
  (e: 'delete-selected-batch'): void
  (e: 'open-detail', item: TaskItem): void
  (e: 'toggle-selection', id: string): void
  (e: 'set-page-size', value: number): void
  (e: 'go-page', delta: number): void
  (e: 'update:jump-page', value: string): void
  (e: 'jump-to-page'): void
}>()

function taskStatusBadgeTone(status: TaskItem['status']): string {
  if (status === 'completed') {
    return 'badge-success'
  }
  if (status === 'failed' || status === 'dead_letter') {
    return 'badge-error'
  }
  if (status === 'running') {
    return 'badge-info'
  }
  if (status === 'pending') {
    return 'badge-warning'
  }
  return 'badge-muted'
}
</script>

<template>
  <main class="manage-grid">
    <article class="panel list-panel">
      <div class="panel-head">
        <h2>任务执行列表</h2>
        <span>最新执行优先</span>
      </div>
      <div class="action-row manage-toolbar">
        <button class="action-btn" @click="emit('open-trigger-pull')">拉取烽火事件</button>
        <button class="action-btn" :disabled="tavilyIngestProcessing" @click="emit('trigger-tavily-ingest')">
          {{ tavilyIngestProcessing ? '采集中...' : 'Tavily专题采集' }}
        </button>
        <button class="action-btn" :disabled="autoReviewProcessing" @click="emit('trigger-auto-review')">
          {{ autoReviewProcessing ? '评审中...' : '一键评审' }}
        </button>
        <button class="action-btn" :disabled="autoQuestionProcessing" @click="emit('trigger-auto-question')">
          {{ autoQuestionProcessing ? '提问中...' : '自动提问' }}
        </button>
        <button class="action-btn" :disabled="locationAnalysisProcessing" @click="emit('trigger-location-analysis')">
          {{ locationAnalysisProcessing ? '分析中...' : '分析位置' }}
        </button>
        <button class="action-btn" @click="emit('open-create-task')">新增任务</button>
        <button class="action-btn" @click="emit('toggle-select-all')">{{ allTasksOnPageSelected ? '取消全选本页' : '全选本页' }}</button>
        <button class="action-btn danger" @click="emit('delete-selected-batch')">批量删除</button>
      </div>
      <div v-if="!hasTasks" class="empty-state">暂无任务数据</div>
      <ul v-else class="event-list">
        <li
          v-for="task in tasks"
          :key="task.id"
          :class="['question-card', { active: selectedTaskId === task.id }]"
          @click="emit('open-detail', task)"
        >
          <div class="row-between">
            <label class="select-row" @click.stop>
              <input type="checkbox" :checked="selectedManageTaskIds.includes(task.id)" @change="emit('toggle-selection', task.id)" />
              <span>选择</span>
            </label>
            <div class="tag-group">
              <span class="badge">{{ task.taskType }}</span>
              <span :class="['badge', taskStatusBadgeTone(task.status)]">{{ task.status }}</span>
            </div>
          </div>
          <p class="item-meta">{{ task.idempotencyKey }}</p>
          <small class="item-subtle">尝试次数：{{ task.attemptCount }} | Trace: {{ task.traceId }}</small>
        </li>
      </ul>
      <div class="action-row pagination-row pagination-center">
        <span>每页</span>
        <select :value="taskManagePageSize" @change="emit('set-page-size', Number(($event.target as HTMLSelectElement).value))">
          <option v-for="size in taskManagePageSizeOptions" :key="`task-page-size-${size}`" :value="size">{{ size }}</option>
        </select>
        <button class="action-btn" @click="emit('go-page', -1)">上一页</button>
        <input :value="taskManageJumpPage" class="jump-input" placeholder="页码" @input="emit('update:jump-page', ($event.target as HTMLInputElement).value)" />
        <button class="action-btn" @click="emit('jump-to-page')">跳转</button>
        <button class="action-btn" @click="emit('go-page', 1)">下一页</button>
      </div>
    </article>
  </main>
</template>

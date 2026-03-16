<script setup lang="ts">
type Level = 'L1' | 'L2' | 'L3' | 'L4'

interface TemplateItem {
  id: string
  questionTemplate: string
  majorTopic: string
  minorTopic: string
  difficultyLevel: Level
  constructionRationale: string
  candidateAnswers: string
  answerDeadline: string
  status: 'active' | 'inactive' | 'archived'
  version: string
  usageCount: number
  createdAt: string
  updatedAt: string
}

defineProps<{
  templateManagePage: number
  templateManageTotalPages: number
  allTemplatesOnPageSelected: boolean
  templateManageSearchKeyword: string
  templateManageTotal: number
  hasTemplates: boolean
  templates: TemplateItem[]
  selectedTemplateId: string
  selectedManageTemplateIds: string[]
  templateManagePageSize: number
  templateManagePageSizeOptions: number[]
  templateManageJumpPage: string
}>()

const emit = defineEmits<{
  (e: 'open-create-template'): void
  (e: 'toggle-select-all'): void
  (e: 'delete-selected-batch'): void
  (e: 'update:search-keyword', value: string): void
  (e: 'open-detail', item: TemplateItem): void
  (e: 'toggle-selection', id: string): void
  (e: 'open-edit', item: TemplateItem): void
  (e: 'set-page-size', value: number): void
  (e: 'go-page', delta: number): void
  (e: 'update:jump-page', value: string): void
  (e: 'jump-to-page'): void
}>()

function templateStatusBadgeTone(status: TemplateItem['status']): string {
  if (status === 'active') {
    return 'badge-success'
  }
  if (status === 'inactive') {
    return 'badge-muted'
  }
  return 'badge-warning'
}
</script>

<template>
  <main class="manage-grid">
    <article class="panel list-panel">
      <div class="panel-head">
        <h2>模板配置列表</h2>
        <span>第 {{ templateManagePage }} / {{ templateManageTotalPages }} 页</span>
      </div>
      <div class="action-row manage-toolbar">
        <button class="action-btn" @click="emit('open-create-template')">新增模板</button>
        <button class="action-btn" @click="emit('toggle-select-all')">{{ allTemplatesOnPageSelected ? '取消全选本页' : '全选本页' }}</button>
        <button class="action-btn danger" @click="emit('delete-selected-batch')">批量删除所选</button>
        <input
          :value="templateManageSearchKeyword"
          class="toolbar-grow"
          placeholder="搜索模板/主题/理由/候选答案"
          @input="emit('update:search-keyword', ($event.target as HTMLInputElement).value)"
        />
        <small class="toolbar-note">匹配 {{ templateManageTotal }} 条</small>
      </div>
      <div v-if="!hasTemplates" class="empty-state">暂无模板数据</div>
      <ul v-else class="event-list">
        <li
          v-for="item in templates"
          :key="`template-${item.id}`"
          :class="['question-card', 'with-actions', { active: selectedTemplateId === item.id }]"
          @click="emit('open-detail', item)"
        >
          <div class="row-between">
            <label class="select-row" @click.stop>
              <input type="checkbox" :checked="selectedManageTemplateIds.includes(item.id)" @change="emit('toggle-selection', item.id)" />
              <span>选择</span>
            </label>
            <strong class="item-title">{{ item.questionTemplate }}</strong>
            <div class="tag-group">
              <span class="badge">{{ item.difficultyLevel }}</span>
              <span :class="['badge', templateStatusBadgeTone(item.status)]">{{ item.status }}</span>
            </div>
          </div>
          <p class="item-meta">{{ item.majorTopic }} / {{ item.minorTopic }}</p>
          <small class="item-subtle">{{ item.candidateAnswers }}</small>
          <div class="action-row action-right card-actions">
            <button class="action-btn" @click.stop="emit('open-edit', item)">编辑</button>
          </div>
        </li>
      </ul>
      <div class="action-row pagination-row pagination-center">
        <span>每页</span>
        <select :value="templateManagePageSize" @change="emit('set-page-size', Number(($event.target as HTMLSelectElement).value))">
          <option v-for="size in templateManagePageSizeOptions" :key="`template-page-size-${size}`" :value="size">{{ size }}</option>
        </select>
        <button class="action-btn" @click="emit('go-page', -1)">上一页</button>
        <input :value="templateManageJumpPage" class="jump-input" placeholder="页码" @input="emit('update:jump-page', ($event.target as HTMLInputElement).value)" />
        <button class="action-btn" @click="emit('jump-to-page')">跳转</button>
        <button class="action-btn" @click="emit('go-page', 1)">下一页</button>
      </div>
    </article>
  </main>
</template>

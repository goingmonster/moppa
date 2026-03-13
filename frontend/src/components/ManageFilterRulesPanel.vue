<script setup lang="ts">
interface FilterRuleItem {
  id: string
  name: string
  level: number
  ruleScope: 'db_import' | 'scrapy' | 'document' | 'use' | 'other'
  filterExpression: string
  filterPrompts: string[]
  filterConfig: Record<string, unknown>
  priority: number
  status: 'active' | 'inactive' | 'archived'
  version: string
  createdAt: string
  updatedAt: string
}

defineProps<{
  allFilterRulesOnPageSelected: boolean
  hasFilterRules: boolean
  filterRules: FilterRuleItem[]
  selectedFilterRuleId: string
  selectedManageFilterRuleIds: string[]
  filterRuleManagePageSize: number
  filterRuleManageJumpPage: string
}>()

const emit = defineEmits<{
  (e: 'open-create'): void
  (e: 'toggle-select-all'): void
  (e: 'delete-selected-batch'): void
  (e: 'open-detail', item: FilterRuleItem): void
  (e: 'toggle-selection', id: string): void
  (e: 'open-edit', item: FilterRuleItem): void
  (e: 'set-page-size', value: number): void
  (e: 'go-page', delta: number): void
  (e: 'update:jump-page', value: string): void
  (e: 'jump-to-page'): void
}>()

function filterRuleStatusBadgeTone(status: FilterRuleItem['status']): string {
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
        <h2>过滤规则列表</h2>
        <span>分页 + 批量操作</span>
      </div>
      <div class="action-row manage-toolbar">
        <button class="action-btn" @click="emit('open-create')">新增规则</button>
        <button class="action-btn" @click="emit('toggle-select-all')">{{ allFilterRulesOnPageSelected ? '取消全选本页' : '全选本页' }}</button>
        <button class="action-btn danger" @click="emit('delete-selected-batch')">批量删除</button>
      </div>
      <div v-if="!hasFilterRules" class="empty-state">暂无过滤规则</div>
      <ul v-else class="event-list">
        <li
          v-for="item in filterRules"
          :key="item.id"
          :class="['question-card', 'with-actions', { active: selectedFilterRuleId === item.id }]"
          @click="emit('open-detail', item)"
        >
          <div class="row-between">
            <label class="select-row" @click.stop>
              <input type="checkbox" :checked="selectedManageFilterRuleIds.includes(item.id)" @change="emit('toggle-selection', item.id)" />
              <span>选择</span>
            </label>
            <div class="tag-group">
              <span class="badge">{{ item.filterExpression }}</span>
              <span class="badge">{{ item.ruleScope }}</span>
              <span :class="['badge', filterRuleStatusBadgeTone(item.status)]">{{ item.status }}</span>
            </div>
          </div>
          <p class="item-title">{{ item.name }} (L{{ item.level }})</p>
          <small class="item-subtle">优先级 {{ item.priority }} | 版本 {{ item.version }}</small>
          <div class="action-row action-right card-actions">
            <button class="action-btn" @click.stop="emit('open-edit', item)">编辑</button>
          </div>
        </li>
      </ul>
      <div class="action-row pagination-row pagination-center">
        <span>每页</span>
        <button :class="['level-btn', { active: filterRuleManagePageSize === 10 }]" @click="emit('set-page-size', 10)">10</button>
        <button :class="['level-btn', { active: filterRuleManagePageSize === 20 }]" @click="emit('set-page-size', 20)">20</button>
        <button :class="['level-btn', { active: filterRuleManagePageSize === 50 }]" @click="emit('set-page-size', 50)">50</button>
        <button class="action-btn" @click="emit('go-page', -1)">上一页</button>
        <input :value="filterRuleManageJumpPage" class="jump-input" placeholder="页码" @input="emit('update:jump-page', ($event.target as HTMLInputElement).value)" />
        <button class="action-btn" @click="emit('jump-to-page')">跳转</button>
        <button class="action-btn" @click="emit('go-page', 1)">下一页</button>
      </div>
    </article>
  </main>
</template>

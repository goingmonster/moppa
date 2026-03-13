<script setup lang="ts">
interface DataSourceItem {
  id: string
  name: string
  sourceSystem: string
  sourceType: 'api' | 'database' | 'file' | 'websocket'
  connectionConfig: Record<string, unknown>
  secretRef: string | null
  credibilityLevel: number
  syncFrequency: string
  isActive: boolean
  version: string
  createdAt: string
  updatedAt: string
}

defineProps<{
  allDataSourcesOnPageSelected: boolean
  hasDataSources: boolean
  dataSources: DataSourceItem[]
  selectedDataSourceId: string
  selectedManageDataSourceIds: string[]
  dataSourceManagePageSize: number
  dataSourceManageJumpPage: string
}>()

const emit = defineEmits<{
  (e: 'open-create'): void
  (e: 'toggle-select-all'): void
  (e: 'delete-selected-batch'): void
  (e: 'open-detail', item: DataSourceItem): void
  (e: 'toggle-selection', id: string): void
  (e: 'open-edit', item: DataSourceItem): void
  (e: 'set-page-size', value: number): void
  (e: 'go-page', delta: number): void
  (e: 'update:jump-page', value: string): void
  (e: 'jump-to-page'): void
}>()

function activeBadgeTone(isActive: boolean): string {
  return isActive ? 'badge-success' : 'badge-muted'
}
</script>

<template>
  <main class="manage-grid">
    <article class="panel list-panel">
      <div class="panel-head">
        <h2>数据源列表</h2>
        <span>分页 + 批量操作</span>
      </div>
      <div class="action-row manage-toolbar">
        <button class="action-btn" @click="emit('open-create')">新增数据源</button>
        <button class="action-btn" @click="emit('toggle-select-all')">{{ allDataSourcesOnPageSelected ? '取消全选本页' : '全选本页' }}</button>
        <button class="action-btn danger" @click="emit('delete-selected-batch')">批量删除</button>
      </div>
      <div v-if="!hasDataSources" class="empty-state">暂无数据源</div>
      <ul v-else class="event-list">
        <li
          v-for="item in dataSources"
          :key="item.id"
          :class="['question-card', 'with-actions', { active: selectedDataSourceId === item.id }]"
          @click="emit('open-detail', item)"
        >
          <div class="row-between">
            <label class="select-row" @click.stop>
              <input type="checkbox" :checked="selectedManageDataSourceIds.includes(item.id)" @change="emit('toggle-selection', item.id)" />
              <span>选择</span>
            </label>
            <div class="tag-group">
              <span class="badge">{{ item.sourceType }}</span>
              <span :class="['badge', activeBadgeTone(item.isActive)]">{{ item.isActive ? 'active' : 'inactive' }}</span>
            </div>
          </div>
          <p class="item-title">{{ item.name }} ({{ item.sourceSystem }})</p>
          <small class="item-subtle">可信度 {{ item.credibilityLevel }} | 频率 {{ item.syncFrequency }}</small>
          <div class="action-row action-right card-actions">
            <button class="action-btn" @click.stop="emit('open-edit', item)">编辑</button>
          </div>
        </li>
      </ul>
      <div class="action-row pagination-row pagination-center">
        <span>每页</span>
        <button :class="['level-btn', { active: dataSourceManagePageSize === 10 }]" @click="emit('set-page-size', 10)">10</button>
        <button :class="['level-btn', { active: dataSourceManagePageSize === 20 }]" @click="emit('set-page-size', 20)">20</button>
        <button :class="['level-btn', { active: dataSourceManagePageSize === 50 }]" @click="emit('set-page-size', 50)">50</button>
        <button class="action-btn" @click="emit('go-page', -1)">上一页</button>
        <input :value="dataSourceManageJumpPage" class="jump-input" placeholder="页码" @input="emit('update:jump-page', ($event.target as HTMLInputElement).value)" />
        <button class="action-btn" @click="emit('jump-to-page')">跳转</button>
        <button class="action-btn" @click="emit('go-page', 1)">下一页</button>
      </div>
    </article>
  </main>
</template>

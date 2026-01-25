<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #409EFF;">
            <el-icon size="32"><Box /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.inventoryCount }}</div>
            <div class="stat-label">库存产品数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #67C23A;">
            <el-icon size="32"><Folder /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.categoryCount }}</div>
            <div class="stat-label">设备分类数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #E6A23C;">
            <el-icon size="32"><DataAnalysis /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.taskCount }}</div>
            <div class="stat-label">分析任务数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #F56C6C;">
            <el-icon size="32"><User /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.userCount }}</div>
            <div class="stat-label">系统用户数</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>快捷操作</span>
          </template>
          <div class="quick-actions">
            <el-button type="primary" @click="$router.push('/inventory')">
              <el-icon><Box /></el-icon> 库存管理
            </el-button>
            <el-button type="success" @click="$router.push('/procurement')">
              <el-icon><DataAnalysis /></el-icon> 采购分析
            </el-button>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>系统信息</span>
          </template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="系统名称">智能采购管理系统</el-descriptions-item>
            <el-descriptions-item label="当前用户">{{ userStore.nickname }}</el-descriptions-item>
            <el-descriptions-item label="角色">{{ userStore.roles.join(', ') || '普通用户' }}</el-descriptions-item>
            <el-descriptions-item label="AI服务">DeepSeek</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useUserStore } from '@/store/user'
import { getInventoryList, getCategories } from '@/api/inventory'
import { getTaskList } from '@/api/procurement'
import { getUserList } from '@/api/system'

const userStore = useUserStore()

const stats = ref({
  inventoryCount: 0,
  categoryCount: 0,
  taskCount: 0,
  userCount: 0
})

onMounted(async () => {
  try {
    const [inventory, categories, tasks] = await Promise.all([
      getInventoryList({ page: 1, page_size: 1 }),
      getCategories(),
      getTaskList({ page: 1, page_size: 1 })
    ])
    
    stats.value.inventoryCount = inventory.total || 0
    stats.value.categoryCount = categories?.length || 0
    stats.value.taskCount = tasks?.length || 0
    
    if (userStore.isAdmin) {
      const users = await getUserList()
      stats.value.userCount = users?.length || 0
    }
  } catch (error) {
    console.error('Failed to load stats:', error)
  }
})
</script>

<style scoped>
.dashboard {
  padding: 10px;
}

.stat-card {
  display: flex;
  align-items: center;
  padding: 20px;
}

.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  width: 100%;
}

.stat-icon {
  width: 64px;
  height: 64px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.stat-info {
  margin-left: 20px;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #333;
}

.stat-label {
  font-size: 14px;
  color: #999;
  margin-top: 5px;
}

.quick-actions {
  display: flex;
  gap: 15px;
}
</style>

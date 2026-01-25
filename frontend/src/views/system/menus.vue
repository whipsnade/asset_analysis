<template>
  <div class="menus-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>菜单管理</span>
          <el-button type="primary" @click="handleAdd(0)">
            <el-icon><Plus /></el-icon> 新增菜单
          </el-button>
        </div>
      </template>

      <el-table :data="tableData" v-loading="loading" row-key="id" border default-expand-all>
        <el-table-column prop="title" label="菜单名称" min-width="150" />
        <el-table-column prop="icon" label="图标" width="80" align="center">
          <template #default="{ row }">
            <el-icon v-if="row.icon"><component :is="row.icon" /></el-icon>
          </template>
        </el-table-column>
        <el-table-column prop="path" label="路由路径" min-width="150" />
        <el-table-column prop="component" label="组件路径" min-width="150" />
        <el-table-column prop="permission" label="权限标识" min-width="150" />
        <el-table-column prop="sort" label="排序" width="80" align="center" />
        <el-table-column prop="menu_type" label="类型" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.menu_type === 1 ? 'warning' : 'success'" size="small">
              {{ row.menu_type === 1 ? '目录' : '菜单' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="handleAdd(row.id)">新增子菜单</el-button>
            <el-button type="danger" link @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Add Dialog -->
    <el-dialog v-model="dialogVisible" title="新增菜单" width="500px">
      <el-form ref="formRef" :model="editForm" :rules="formRules" label-width="80px">
        <el-form-item label="菜单名称" prop="title">
          <el-input v-model="editForm.title" />
        </el-form-item>
        <el-form-item label="菜单类型">
          <el-radio-group v-model="editForm.menu_type">
            <el-radio :value="1">目录</el-radio>
            <el-radio :value="2">菜单</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="路由路径" prop="path">
          <el-input v-model="editForm.path" placeholder="/path" />
        </el-form-item>
        <el-form-item label="组件路径" prop="component">
          <el-input v-model="editForm.component" placeholder="views/xxx/index" />
        </el-form-item>
        <el-form-item label="图标" prop="icon">
          <el-input v-model="editForm.icon" placeholder="Element Plus 图标名称" />
        </el-form-item>
        <el-form-item label="权限标识" prop="permission">
          <el-input v-model="editForm.permission" placeholder="system:user:list" />
        </el-form-item>
        <el-form-item label="排序" prop="sort">
          <el-input-number v-model="editForm.sort" :min="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getMenuList, createMenu, deleteMenu } from '@/api/system'

const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const tableData = ref([])
const formRef = ref(null)

const editForm = reactive({
  parent_id: 0,
  title: '',
  path: '',
  component: '',
  icon: '',
  sort: 0,
  menu_type: 2,
  permission: ''
})

const formRules = {
  title: [{ required: true, message: '请输入菜单名称', trigger: 'blur' }]
}

const loadData = async () => {
  loading.value = true
  try {
    tableData.value = await getMenuList()
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  Object.assign(editForm, {
    parent_id: 0,
    title: '',
    path: '',
    component: '',
    icon: '',
    sort: 0,
    menu_type: 2,
    permission: ''
  })
}

const handleAdd = (parentId) => {
  resetForm()
  editForm.parent_id = parentId
  dialogVisible.value = true
}

const handleSubmit = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    await createMenu(editForm)
    ElMessage.success('创建成功')
    dialogVisible.value = false
    loadData()
  } finally {
    submitting.value = false
  }
}

const handleDelete = (row) => {
  ElMessageBox.confirm('确定要删除该菜单吗？', '提示', { type: 'warning' })
    .then(async () => {
      await deleteMenu(row.id)
      ElMessage.success('删除成功')
      loadData()
    })
    .catch(() => {})
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>

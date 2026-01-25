<template>
  <div class="roles-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>角色管理</span>
          <el-button type="primary" @click="handleAdd">
            <el-icon><Plus /></el-icon> 新增角色
          </el-button>
        </div>
      </template>

      <el-table :data="tableData" v-loading="loading" stripe border>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="role_name" label="角色名称" width="150" />
        <el-table-column prop="role_key" label="角色标识" width="150" />
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'">
              {{ row.status === 1 ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="create_time" label="创建时间" min-width="170">
          <template #default="{ row }">
            {{ formatDate(row.create_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="handleEdit(row)">编辑</el-button>
            <el-button type="success" link @click="handleAssignMenus(row)">分配权限</el-button>
            <el-button type="danger" link @click="handleDelete(row)" :disabled="row.role_key === 'admin'">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Edit Dialog -->
    <el-dialog v-model="dialogVisible" :title="editForm.id ? '编辑角色' : '新增角色'" width="400px">
      <el-form ref="formRef" :model="editForm" :rules="formRules" label-width="80px">
        <el-form-item label="角色名称" prop="role_name">
          <el-input v-model="editForm.role_name" />
        </el-form-item>
        <el-form-item label="角色标识" prop="role_key">
          <el-input v-model="editForm.role_key" :disabled="!!editForm.id" />
        </el-form-item>
        <el-form-item v-if="editForm.id" label="状态">
          <el-switch v-model="editForm.status" :active-value="1" :inactive-value="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- Assign Menus Dialog -->
    <el-dialog v-model="menuDialogVisible" title="分配权限" width="400px">
      <el-tree
        ref="menuTreeRef"
        :data="menuTree"
        :props="{ label: 'title', children: 'children' }"
        show-checkbox
        node-key="id"
        default-expand-all
      />
      <template #footer>
        <el-button @click="menuDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSaveMenus">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getRoleList, createRole, updateRole, deleteRole, getRoleMenus, assignRoleMenus, getMenuList } from '@/api/system'

const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const menuDialogVisible = ref(false)
const tableData = ref([])
const menuTree = ref([])
const currentRoleId = ref(null)
const formRef = ref(null)
const menuTreeRef = ref(null)

const editForm = reactive({
  id: null,
  role_name: '',
  role_key: '',
  status: 1
})

const formRules = {
  role_name: [{ required: true, message: '请输入角色名称', trigger: 'blur' }],
  role_key: [{ required: true, message: '请输入角色标识', trigger: 'blur' }]
}

const formatDate = (date) => {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}

const loadData = async () => {
  loading.value = true
  try {
    tableData.value = await getRoleList()
  } finally {
    loading.value = false
  }
}

const loadMenus = async () => {
  try {
    menuTree.value = await getMenuList()
  } catch (error) {
    console.error(error)
  }
}

const resetForm = () => {
  Object.assign(editForm, { id: null, role_name: '', role_key: '', status: 1 })
}

const handleAdd = () => {
  resetForm()
  dialogVisible.value = true
}

const handleEdit = (row) => {
  Object.assign(editForm, row)
  dialogVisible.value = true
}

const handleSubmit = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (editForm.id) {
      await updateRole(editForm.id, editForm)
      ElMessage.success('更新成功')
    } else {
      await createRole(editForm)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
  } finally {
    submitting.value = false
  }
}

const handleDelete = (row) => {
  ElMessageBox.confirm('确定要删除该角色吗？', '提示', { type: 'warning' })
    .then(async () => {
      await deleteRole(row.id)
      ElMessage.success('删除成功')
      loadData()
    })
    .catch(() => {})
}

const handleAssignMenus = async (row) => {
  currentRoleId.value = row.id
  menuDialogVisible.value = true
  
  try {
    const menuIds = await getRoleMenus(row.id)
    menuTreeRef.value?.setCheckedKeys(menuIds)
  } catch (error) {
    console.error(error)
  }
}

const handleSaveMenus = async () => {
  const checkedKeys = menuTreeRef.value?.getCheckedKeys() || []
  const halfCheckedKeys = menuTreeRef.value?.getHalfCheckedKeys() || []
  const allKeys = [...checkedKeys, ...halfCheckedKeys]

  submitting.value = true
  try {
    await assignRoleMenus(currentRoleId.value, allKeys)
    ElMessage.success('分配成功')
    menuDialogVisible.value = false
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadData()
  loadMenus()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>

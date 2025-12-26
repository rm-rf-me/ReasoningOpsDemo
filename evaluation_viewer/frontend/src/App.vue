<template>
  <div id="app">
    <a-layout class="layout">
      <!-- 顶部导航 -->
      <a-layout-header class="header">
        <div class="logo">
          <h2 style="color: white; margin: 0">评测结果展示系统</h2>
        </div>
        <div class="header-info">
          <a-tooltip v-if="configPaths.excel_dir_path" :title="configPaths.excel_dir_path">
            <span class="path-info">
              <FileOutlined /> Excel: {{ truncatePath(configPaths.excel_dir_path) }}
            </span>
          </a-tooltip>
          <a-tooltip v-if="configPaths.results_file_path" :title="configPaths.results_file_path">
            <span class="path-info">
              <FileTextOutlined /> 结果: {{ truncatePath(configPaths.results_file_path) }}
            </span>
          </a-tooltip>
        </div>
        <div class="header-actions">
          <a-button type="primary" @click="showUploadModal">
            <template #icon><UploadOutlined /></template>
            上传数据
          </a-button>
        </div>
      </a-layout-header>

      <!-- 主体内容 -->
      <a-layout-content class="content">
        <router-view />
      </a-layout-content>

      <!-- 底部 -->
      <a-layout-footer class="footer">
        评测结果展示系统 ©2024
      </a-layout-footer>
    </a-layout>

    <!-- 上传模态框 -->
    <UploadModal
      v-model:open="uploadModalVisible"
      @uploaded="handleUploaded"
    />
  </div>
</template>

<script>
import { UploadOutlined, FileOutlined, FileTextOutlined } from '@ant-design/icons-vue'
import UploadModal from './components/UploadModal.vue'
import axios from 'axios'

export default {
  name: 'App',
  components: {
    UploadOutlined,
    FileOutlined,
    FileTextOutlined,
    UploadModal
  },
  data() {
    return {
      uploadModalVisible: false,
      configPaths: {
        excel_dir_path: null,
        results_file_path: null,
        excel_files_count: 0,
        results_count: 0
      }
    }
  },
  async created() {
    await this.loadConfigPaths()
    // 监听路由变化，刷新配置信息
    this.$router.afterEach(() => {
      this.loadConfigPaths()
    })
  },
  methods: {
    showUploadModal() {
      this.uploadModalVisible = true
    },
    handleUploaded() {
      this.uploadModalVisible = false
      // 刷新配置信息
      this.loadConfigPaths()
      // 刷新当前页面数据
      this.$router.go(0)
    },
    async loadConfigPaths() {
      try {
        const response = await axios.get('/config/paths')
        this.configPaths = response.data
      } catch (error) {
        console.error('加载配置路径失败:', error)
      }
    },
    truncatePath(path) {
      if (!path) return '-'
      if (path.length <= 40) return path
      return '...' + path.slice(-37)
    }
  }
}
</script>

<style>
.layout {
  min-height: 100vh;
}

.header {
  background: #001529;
  padding: 0 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo {
  display: flex;
  align-items: center;
}

.header-info {
  display: flex;
  gap: 20px;
  align-items: center;
  flex: 1;
  margin: 0 20px;
}

.path-info {
  color: rgba(255, 255, 255, 0.85);
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.content {
  padding: 20px;
  background: #f0f2f5;
  min-height: calc(100vh - 134px);
}

.footer {
  text-align: center;
  background: #fafafa;
}

/* 全局样式 */
.ant-table-tbody > tr:hover > td {
  background: #f5f5f5;
}

.ant-card-body {
  padding: 16px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .header {
    padding: 0 10px;
  }

  .content {
    padding: 10px;
  }
}
</style>

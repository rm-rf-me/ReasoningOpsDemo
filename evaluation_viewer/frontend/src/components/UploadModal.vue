<template>
  <a-modal
    v-model:open="visible"
    title="配置数据路径"
    width="700px"
    :footer="null"
    :destroyOnClose="true"
  >
    <div class="upload-modal">
      <!-- 步骤1: 扫描Excel文件 -->
      <a-card title="步骤1: 扫描Excel文件" class="upload-card">
        <a-form layout="vertical">
          <a-form-item label="Excel数据目录路径">
            <a-input
              v-model:value="excelDirPath"
              placeholder="./data 或 /path/to/excel/files"
              :disabled="scanning || excelFilesScanned"
            >
              <template #prefix>
                <FolderOpenOutlined />
              </template>
            </a-input>
            <div class="form-hint">
              <a-button
                type="link"
                @click="selectDirectory"
                :disabled="scanning || excelFilesScanned"
                style="padding: 0; height: auto;"
              >
                📁 选择目录
              </a-button>
              <span style="margin: 0 8px">|</span>
              <a-button
                type="link"
                @click="showDirectoryPicker"
                :disabled="scanning || excelFilesScanned"
                style="padding: 0; height: auto;"
              >
                📝 快速选择常用路径
              </a-button>
            </div>
          </a-form-item>
          <a-form-item>
            <a-button
              type="primary"
              @click="scanExcelFiles"
              :loading="scanning"
              :disabled="!excelDirPath || excelFilesScanned"
            >
              {{ excelFilesScanned ? '✅ 已扫描' : '🔍 扫描Excel文件' }}
            </a-button>
          </a-form-item>
        </a-form>

        <!-- 扫描结果 -->
        <div v-if="excelFilesScanned && scannedExcelFiles.length > 0" class="scan-result">
          <a-alert
            message="扫描成功"
            :description="`共找到 ${scannedExcelFiles.length} 个Excel文件`"
            type="success"
            show-icon
            style="margin-bottom: 12px"
          />
          <div class="excel-files-list">
            <div
              v-for="(file, index) in scannedExcelFiles"
              :key="index"
              class="excel-file-item"
            >
              <FileTextOutlined style="margin-right: 8px; color: #1890ff" />
              <span>{{ file }}</span>
            </div>
          </div>
        </div>
        <div v-else-if="excelFilesScanned && scannedExcelFiles.length === 0" class="scan-result">
          <a-alert
            message="未找到Excel文件"
            description="请确认目录路径是否正确，或目录下是否包含 .xlsx 或 .xls 文件"
            type="warning"
            show-icon
          />
        </div>
      </a-card>

      <!-- 步骤2: 上传结果文件 -->
      <a-card title="步骤2: 上传评测结果文件" class="upload-card">
        <a-form layout="vertical">
          <a-form-item label="评测结果文件路径">
            <a-input
              v-model:value="resultsFilePath"
              placeholder="./results/model_output.jsonl 或 /absolute/path/to/file.jsonl"
              :disabled="uploading || resultsFileLoaded"
            >
              <template #prefix>
                <FileTextOutlined />
              </template>
            </a-input>
            <div class="form-hint">
              <span>输入包含模型预测结果的 .jsonl 文件路径（本地路径）</span>
            </div>
          </a-form-item>
          <a-form-item>
            <a-button
              type="primary"
              @click="loadResultsFile"
              :loading="uploading"
              :disabled="!resultsFilePath || resultsFileLoaded || !excelFilesScanned"
            >
              {{ resultsFileLoaded ? '✅ 已加载' : '📄 加载结果文件' }}
            </a-button>
          </a-form-item>
        </a-form>

        <div v-if="resultsFileLoaded" class="load-result">
          <a-alert
            message="文件加载成功"
            :description="`共加载 ${resultsFileStats.total_records || 0} 条记录`"
            type="success"
            show-icon
          />
        </div>
      </a-card>

      <!-- 步骤3: 开始分析 -->
      <a-card title="步骤3: 开始分析" class="upload-card">
        <a-button
          type="primary"
          size="large"
          @click="startAnalysis"
          :loading="analyzing"
          :disabled="!excelFilesScanned || !resultsFileLoaded"
          block
        >
          🚀 开始分析
        </a-button>
        <div v-if="!excelFilesScanned || !resultsFileLoaded" class="form-hint" style="margin-top: 8px; text-align: center;">
          <span v-if="!excelFilesScanned">请先完成步骤1：扫描Excel文件</span>
          <span v-else-if="!resultsFileLoaded">请先完成步骤2：加载结果文件</span>
        </div>
      </a-card>

      <!-- 操作按钮 -->
      <div class="modal-footer">
        <a-space>
          <a-button @click="clearData" :loading="clearing" danger>
            清空数据
          </a-button>
          <a-button @click="closeModal">
            关闭
          </a-button>
        </a-space>
      </div>
    </div>
  </a-modal>
</template>

<script>
import {
  FileTextOutlined,
  FolderOpenOutlined
} from '@ant-design/icons-vue'
import axios from 'axios'
import { message } from 'ant-design-vue'

export default {
  name: 'UploadModal',
  components: {
    FileTextOutlined,
    FolderOpenOutlined
  },
  props: {
    open: {
      type: Boolean,
      default: false
    }
  },
  emits: ['update:open', 'uploaded'],
  data() {
    return {
      clearing: false,
      analyzing: false,
      scanning: false,
      uploading: false,
      resultsFilePath: '',
      excelDirPath: './data',
      excelFilesScanned: false,
      scannedExcelFiles: [],
      resultsFileLoaded: false,
      resultsFileStats: {}
    }
  },
  computed: {
    visible: {
      get() {
        return this.open
      },
      set(value) {
        this.$emit('update:open', value)
      }
    }
  },
  methods: {
    // 选择目录（使用HTML5文件选择器）
    selectDirectory() {
      const input = document.createElement('input')
      input.type = 'file'
      input.webkitdirectory = true
      input.directory = true
      input.multiple = false

      input.addEventListener('change', (event) => {
        const files = event.target.files
        if (files.length > 0) {
          const file = files[0]
          // 尝试获取目录路径
          if (file.path) {
            // Chrome/Edge支持
            const dirPath = file.path.replace(`/${file.name}`, '')
            this.excelDirPath = dirPath
            message.success(`已选择目录: ${dirPath}`)
          } else if (file.webkitRelativePath) {
            // 其他浏览器，使用相对路径
            const dirPath = file.webkitRelativePath.split('/')[0]
            this.excelDirPath = dirPath
            message.info(`已选择目录: ${dirPath}（相对路径）`)
          } else {
            message.warning('无法获取完整路径，请手动输入目录路径')
          }
        }
      })

      input.click()
    },

    // 扫描Excel文件
    async scanExcelFiles() {
      if (!this.excelDirPath) {
        message.error('请先选择或输入Excel目录路径')
        return
      }

      this.scanning = true
      this.excelFilesScanned = false
      this.scannedExcelFiles = []

      try {
        const response = await axios.post('/scan/excel', {
          excel_dir: this.excelDirPath
        })

        this.scannedExcelFiles = response.data.excel_files || []
        this.excelFilesScanned = true

        if (this.scannedExcelFiles.length > 0) {
          message.success(`扫描成功！找到 ${this.scannedExcelFiles.length} 个Excel文件`)
        } else {
          message.warning('未找到Excel文件，请确认目录路径是否正确')
        }

      } catch (error) {
        console.error('扫描Excel文件失败:', error)
        message.error('扫描Excel文件失败：' + (error.response?.data?.error || error.message))
        this.excelFilesScanned = false
      } finally {
        this.scanning = false
      }
    },

    // 加载结果文件
    async loadResultsFile() {
      if (!this.resultsFilePath) {
        message.error('请先输入评测结果文件路径')
        return
      }

      this.uploading = true
      this.resultsFileLoaded = false

      try {
        const response = await axios.post('/load/results', {
          results_path: this.resultsFilePath
        })

        this.resultsFileStats = {
          total_records: response.data.total_records || 0,
          categories: response.data.categories || []
        }
        this.resultsFileLoaded = true

        message.success(`文件加载成功！共 ${this.resultsFileStats.total_records} 条记录`)

      } catch (error) {
        console.error('加载结果文件失败:', error)
        message.error('加载结果文件失败：' + (error.response?.data?.error || error.message))
        this.resultsFileLoaded = false
      } finally {
        this.uploading = false
      }
    },

    // 开始分析
    async startAnalysis() {
      if (!this.excelFilesScanned || !this.resultsFileLoaded) {
        message.error('请先完成步骤1和步骤2')
        return
      }

      this.analyzing = true

      try {
        // 调用分析API（此时Excel文件已经扫描，结果文件已经加载）
        const response = await axios.post('/analysis/start', {
          excel_dir: this.excelDirPath,
          results_path: this.resultsFilePath
        })

        message.success('数据分析完成！')

        // 关闭模态框并通知父组件
        this.visible = false
        this.$emit('uploaded')

      } catch (error) {
        console.error('数据分析失败:', error)
        message.error('数据分析失败：' + (error.response?.data?.error || error.message))
      } finally {
        this.analyzing = false
      }
    },

    async clearData() {
      this.clearing = true

      try {
        await axios.delete('/data')

        // 清空本地状态
        this.resultsFilePath = ''
        this.excelDirPath = './data'
        this.excelFilesScanned = false
        this.scannedExcelFiles = []
        this.resultsFileLoaded = false
        this.resultsFileStats = {}

        message.success('数据已清空')

        // 通知父组件
        this.$emit('uploaded')

      } catch (error) {
        console.error('清空数据失败:', error)
        message.error('清空数据失败')
      } finally {
        this.clearing = false
      }
    },

    showDirectoryPicker() {
      // 显示预设的目录选项
      const directories = [
        { label: '当前目录 (./)', value: './' },
        { label: 'data目录 (./data)', value: './data' },
        { label: 'excel目录 (./excel)', value: './excel' },
        { label: 'results目录 (./results)', value: './results' },
        { label: '上级data目录 (../data)', value: '../data' },
        { label: '上级excel目录 (../excel)', value: '../excel' },
        { label: '自定义路径', value: 'custom' }
      ]

      // 创建选择模态框
      const options = directories.map(dir => `<option value="${dir.value}">${dir.label}</option>`).join('')

      const modalContent = `
        <div style="padding: 20px;">
          <h4>选择Excel数据目录</h4>
          <select id="dir-select" style="width: 100%; padding: 8px; margin: 10px 0; border: 1px solid #d9d9d9; border-radius: 4px;">
            ${options}
          </select>
          <div id="custom-input" style="display: none; margin-top: 10px;">
            <input type="text" id="custom-dir" placeholder="输入自定义路径" style="width: 100%; padding: 8px; border: 1px solid #d9d9d9; border-radius: 4px;">
          </div>
          <div style="margin-top: 20px; text-align: right;">
            <button id="cancel-btn" style="margin-right: 10px; padding: 6px 12px; border: 1px solid #d9d9d9; background: white; border-radius: 4px; cursor: pointer;">取消</button>
            <button id="confirm-btn" style="padding: 6px 12px; background: #1890ff; color: white; border: none; border-radius: 4px; cursor: pointer;">确定</button>
          </div>
        </div>
      `

      // 创建模态框
      const modal = document.createElement('div')
      modal.style.cssText = `
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.5); z-index: 2000;
        display: flex; align-items: center; justify-content: center;
      `
      modal.innerHTML = modalContent
      document.body.appendChild(modal)

      // 绑定事件
      const select = modal.querySelector('#dir-select')
      const customInput = modal.querySelector('#custom-input')
      const cancelBtn = modal.querySelector('#cancel-btn')
      const confirmBtn = modal.querySelector('#confirm-btn')

      select.addEventListener('change', function() {
        if (this.value === 'custom') {
          customInput.style.display = 'block'
        } else {
          customInput.style.display = 'none'
        }
      })

      cancelBtn.addEventListener('click', () => {
        document.body.removeChild(modal)
      })

      confirmBtn.addEventListener('click', () => {
        let selectedPath = select.value
        if (selectedPath === 'custom') {
          const customPath = modal.querySelector('#custom-dir').value.trim()
          if (customPath) {
            selectedPath = customPath
          } else {
            alert('请输入自定义路径')
            return
          }
        }
        this.excelDirPath = selectedPath
        document.body.removeChild(modal)
      })
    },

    showDirectoryPicker() {
      // 显示预设的目录选项
      const directories = [
        { label: '当前目录 (./)', value: './' },
        { label: 'data目录 (./data)', value: './data' },
        { label: 'excel目录 (./excel)', value: './excel' },
        { label: 'results目录 (./results)', value: './results' },
        { label: '上级data目录 (../data)', value: '../data' },
        { label: '上级excel目录 (../excel)', value: '../excel' },
        { label: '自定义路径', value: 'custom' }
      ]

      // 创建选择模态框
      const options = directories.map(dir => `<option value="${dir.value}">${dir.label}</option>`).join('')

      const modalContent = `
        <div style="padding: 20px;">
          <h4>选择Excel数据目录</h4>
          <select id="dir-select" style="width: 100%; padding: 8px; margin: 10px 0; border: 1px solid #d9d9d9; border-radius: 4px;">
            ${options}
          </select>
          <div id="custom-input" style="display: none; margin-top: 10px;">
            <input type="text" id="custom-dir" placeholder="输入自定义路径（如：/Users/username/data）" style="width: 100%; padding: 8px; border: 1px solid #d9d9d9; border-radius: 4px;">
          </div>
          <div style="margin-top: 20px; text-align: right;">
            <button id="cancel-btn" style="margin-right: 10px; padding: 6px 12px; border: 1px solid #d9d9d9; background: white; border-radius: 4px; cursor: pointer;">取消</button>
            <button id="confirm-btn" style="padding: 6px 12px; background: #1890ff; color: white; border: none; border-radius: 4px; cursor: pointer;">确定</button>
          </div>
        </div>
      `

      // 创建模态框
      const modal = document.createElement('div')
      modal.style.cssText = `
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.5); z-index: 2000;
        display: flex; align-items: center; justify-content: center;
      `
      modal.innerHTML = modalContent
      document.body.appendChild(modal)

      // 绑定事件
      const select = modal.querySelector('#dir-select')
      const customInput = modal.querySelector('#custom-input')
      const cancelBtn = modal.querySelector('#cancel-btn')
      const confirmBtn = modal.querySelector('#confirm-btn')

      select.addEventListener('change', function() {
        if (this.value === 'custom') {
          customInput.style.display = 'block'
        } else {
          customInput.style.display = 'none'
        }
      })

      cancelBtn.addEventListener('click', () => {
        document.body.removeChild(modal)
      })

      confirmBtn.addEventListener('click', () => {
        let selectedPath = select.value
        if (selectedPath === 'custom') {
          const customPath = modal.querySelector('#custom-dir').value.trim()
          if (customPath) {
            selectedPath = customPath
          } else {
            message.error('请输入自定义路径')
            return
          }
        }
        this.excelDirPath = selectedPath
        message.success('Excel目录已配置')
        document.body.removeChild(modal)
      })
    },

    closeModal() {
      this.visible = false
    }
  }
}
</script>

<style scoped>
.upload-modal {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.upload-card {
  margin-bottom: 16px;
}

.upload-result {
  margin-top: 16px;
}

.upload-stats {
  margin-top: 12px;
  padding: 12px;
  background: #f6f8fa;
  border-radius: 4px;
}

.upload-stats p {
  margin: 4px 0;
  font-size: 14px;
}

.upload-stats ul {
  margin: 8px 0;
  padding-left: 20px;
}

.form-hint {
  font-size: 12px;
  color: #666;
  margin-top: 4px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  padding-top: 16px;
  border-top: 1px solid #e8e8e8;
}

.scan-result {
  margin-top: 16px;
}

.excel-files-list {
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  padding: 8px;
  background: #fafafa;
}

.excel-file-item {
  padding: 6px 8px;
  margin: 4px 0;
  background: white;
  border-radius: 4px;
  font-size: 13px;
  display: flex;
  align-items: center;
}

.load-result {
  margin-top: 16px;
}
</style>

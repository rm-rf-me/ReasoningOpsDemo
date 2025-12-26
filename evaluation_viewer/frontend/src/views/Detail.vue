<template>
  <div class="detail" v-loading="loading">
    <!-- 返回按钮 -->
    <div class="back-button">
      <a-button @click="goBack">
        <template #icon><ArrowLeftOutlined /></template>
        返回列表
      </a-button>
    </div>

    <!-- 导航按钮 -->
    <div class="navigation" v-if="navigation">
      <a-space direction="vertical" style="width: 100%">
        <!-- 筛选信息提示 -->
        <div v-if="hasActiveFilters && filterInfoVisible" class="filter-info">
          <a-alert
            type="info"
            :message="filterInfoText"
            :description="`当前筛选后共 ${navigation.total} 条记录`"
            show-icon
            closable
            @close="filterInfoVisible = false"
          />
        </div>
        <!-- 导航按钮 -->
        <a-space>
          <a-button
            :disabled="!navigation.previous"
            @click="goToResult(navigation.previous)"
          >
            <template #icon><LeftOutlined /></template>
            上一条
          </a-button>

          <span class="page-info">
            {{ navigation.current_index }} / {{ navigation.total }}
            <span v-if="hasActiveFilters" style="color: #1890ff; margin-left: 8px">
              (筛选后)
            </span>
          </span>

          <a-button
            :disabled="!navigation.next"
            @click="goToResult(navigation.next)"
          >
            下一条
            <template #icon><RightOutlined /></template>
          </a-button>
        </a-space>
      </a-space>
    </div>

    <!-- 结果详情 -->
    <div v-if="result" class="result-detail">
      <!-- 元数据概览 -->
      <a-card class="meta-card" title="基本信息">
        <a-row :gutter="16">
          <a-col :span="6">
            <div class="meta-item">
              <span class="label">告警ID:</span>
              <a-typography-text copyable>{{ result.alarm_id }}</a-typography-text>
            </div>
          </a-col>
          <a-col :span="6">
            <div class="meta-item">
              <span class="label">Excel文件:</span>
              <span>{{ getExcelFileName(result) }}</span>
            </div>
          </a-col>
          <a-col :span="6">
            <div class="meta-item">
              <span class="label">Sheet名:</span>
              <span>{{ getSheetName(result) }}</span>
            </div>
          </a-col>
          <a-col :span="6">
            <div class="meta-item">
              <span class="label">场景分类:</span>
              <a-tag color="blue">{{ result.meta?.category || '-' }}</a-tag>
            </div>
          </a-col>
          <a-col :span="6">
            <div class="meta-item">
              <span class="label">预测结果:</span>
              <div class="prediction-tags">
                <a-tag :color="getPredictionTagColor(result)" style="margin-right: 4px;">
                  {{ getPredictionLabelDisplay(result) }}
                </a-tag>
                <a-tag
                  :color="result.correct ? 'green' : result.predicted_label === null ? 'orange' : 'red'"
                >
                  {{ getCorrectnessText(result) }}
                </a-tag>
              </div>
            </div>
          </a-col>
        </a-row>
      </a-card>

      <!-- 模型输入 -->
      <a-card title="模型输入" class="input-card" style="margin-bottom: 20px">
        <pre class="content-text">{{ result.input }}</pre>
      </a-card>

      <!-- 输出对比 -->
      <a-card class="comparison-card" title="输出对比分析" style="margin-bottom: 20px">
        <a-row :gutter="16">
          <a-col :span="12">
            <div class="comparison-section">
              <h4>人工标注输出</h4>
              <pre class="comparison-text">{{ result.expected_output }}</pre>
            </div>
          </a-col>
          <a-col :span="12">
            <div class="comparison-section">
              <h4>模型输出</h4>
              <pre class="comparison-text">{{ result.model_output }}</pre>
            </div>
          </a-col>
        </a-row>
      </a-card>

      <!-- Excel上下文 -->
      <a-card class="excel-card" title="Excel上下文">
        <template #extra>
          <a-button
            type="primary"
            @click="loadExcelContext"
            :loading="excelLoading"
            :disabled="!canLoadExcel"
          >
            <template #icon><FileTextOutlined /></template>
            {{ excelData ? '重新加载' : '加载上下文' }}
          </a-button>
        </template>

        <!-- 按钮禁用原因提示 -->
        <div v-if="!canLoadExcel && result" class="excel-disabled-hint">
          <a-alert
            :message="getExcelDisabledReason()"
            type="warning"
            show-icon
            style="margin-bottom: 16px;"
          />
        </div>

        <div v-if="excelError" class="excel-error">
          <a-alert
            :message="excelError"
            type="error"
            show-icon
            :description="excelError.includes('未找到匹配') ? '请检查Excel文件路径配置，或确认文件名是否正确。' : ''"
          />
        </div>

        <div v-else-if="excelLoading" class="excel-loading">
          <a-spin size="large" tip="正在加载Excel数据...">
            <div style="height: 200px"></div>
          </a-spin>
        </div>

        <div v-else-if="excelData && excelData.length > 0" class="excel-table-container">
          <a-table
            :columns="excelColumns"
            :dataSource="excelData"
            :pagination="{ pageSize: 20, showSizeChanger: true }"
            :scroll="{ x: 'max-content', y: 400 }"
            size="small"
            bordered
          />
        </div>

        <a-empty
          v-else
          description="点击「加载上下文」按钮加载Excel数据"
          :image="false"
        />
      </a-card>
    </div>

    <!-- 错误状态 -->
    <a-result
      v-else-if="error"
      status="error"
      title="加载失败"
      :sub-title="error"
    >
      <template #extra>
        <a-button type="primary" @click="retryLoad">
          重试
        </a-button>
      </template>
    </a-result>
  </div>
</template>

<script>
import { ArrowLeftOutlined, LeftOutlined, RightOutlined, FileTextOutlined } from '@ant-design/icons-vue'
import { mapState, mapActions } from 'vuex'
import axios from 'axios'

export default {
  name: 'Detail',
  components: {
    ArrowLeftOutlined,
    LeftOutlined,
    RightOutlined,
    FileTextOutlined
  },
  props: {
    alarmId: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      navigation: null,
      navLoading: false,
      excelLoading: false,
      excelData: null,
      excelError: null,
      excelColumns: [],
      filterInfoVisible: true
    }
  },
  computed: {
    ...mapState('results', ['currentResult', 'loading', 'error']),
    ...mapState('filters', ['filters']),

    result() {
      return this.currentResult
    },

    // 从路由参数获取alarmId（如果props中没有）
    routeAlarmId() {
      return this.$route.params.alarmId || this.alarmId
    },

    hasActiveFilters() {
      return !!(this.filters.search || this.filters.category || this.filters.correctness)
    },

    filterInfoText() {
      const parts = []
      if (this.filters.search) {
        parts.push(`搜索: "${this.filters.search}"`)
      }
      if (this.filters.category) {
        parts.push(`场景分类: ${this.filters.category}`)
      }
      if (this.filters.correctness) {
        const correctnessMap = {
          'correct': '正确',
          'incorrect': '错误',
          'parse_failed': '解析失败'
        }
        parts.push(`预测结果: ${correctnessMap[this.filters.correctness] || this.filters.correctness}`)
      }
      return parts.length > 0 ? `当前筛选: ${parts.join(', ')}` : ''
    }
  },
  async created() {
    await this.loadData()
  },
  watch: {
    alarmId: {
      handler: 'loadData',
      immediate: false
    },
    '$route.params.alarmId': {
      handler: 'loadData',
      immediate: false
    },
    // 监听筛选条件变化，重新加载导航
    'filters.search': {
      handler: 'loadNavigation',
      immediate: false
    },
    'filters.category': {
      handler: 'loadNavigation',
      immediate: false
    },
    'filters.correctness': {
      handler: 'loadNavigation',
      immediate: false
    }
  },
  methods: {
    ...mapActions('results', ['fetchResultDetail']),

    async loadData() {
      // 获取alarmId（优先使用路由参数）
      const targetAlarmId = this.$route?.params?.alarmId || this.alarmId
      
      if (!targetAlarmId) {
        console.error('缺少告警ID，无法加载数据')
        return
      }

      // 加载结果详情（不自动加载Excel）
      await this.fetchResultDetail(targetAlarmId)

      // 加载导航信息
      await this.loadNavigation()

      // 重置Excel相关状态
      this.excelData = null
      this.excelError = null
      this.excelColumns = []
    },

    async loadNavigation() {
      const targetAlarmId = this.$route?.params?.alarmId || this.alarmId
      if (!targetAlarmId) return
      
      this.navLoading = true
      try {
        // 构建查询参数，传递当前筛选条件
        const params = new URLSearchParams()
        if (this.filters.search) {
          params.append('search', this.filters.search)
        }
        if (this.filters.category) {
          params.append('category', this.filters.category)
        }
        if (this.filters.correctness) {
          params.append('correctness', this.filters.correctness)
        }
        
        const queryString = params.toString()
        const url = `/results/${targetAlarmId}/navigation${queryString ? '?' + queryString : ''}`
        const response = await axios.get(url)
        this.navigation = response.data
      } catch (error) {
        console.error('加载导航信息失败:', error)
      } finally {
        this.navLoading = false
      }
    },

    goBack() {
      // 使用push而不是go(-1)，确保路由历史正确
      this.$router.push({ name: 'Home' })
    },

    goToResult(alarmId) {
      if (alarmId) {
        // 使用push而不是replace，以支持浏览器前进后退
        this.$router.push({ name: 'Detail', params: { alarmId } })
      }
    },

    getPredictionTagColor(result) {
      if (!result || result.predicted_label === null) return 'orange'
      return result.correct ? 'green' : 'red'
    },

    getPredictionLabelDisplay(result) {
      if (!result) return '-'
      if (result.predicted_label === null) return '解析失败'
      if (result.predicted_label === 'convergent') return '收敛'
      if (result.predicted_label === 'non_convergent') return '不收敛'
      return result.predicted_label || '-'
    },

    getCorrectnessText(result) {
      if (!result || result.predicted_label === null) return '解析失败'
      return result.correct ? '正确' : '错误'
    },

    getExcelFileName(result) {
      if (!result || !result.meta || !result.meta.scenario_id) return '-'
      const scenarioId = result.meta.scenario_id
      // 场景ID格式: Excel文件名_Sheet名（从最后一个下划线拆分）
      // 例如："冷塔加减机_BJ4-25年BA报警-冷却塔加减机52个-AIOS_4.7-1"
      // Excel文件名：冷塔加减机_BJ4-25年BA报警-冷却塔加减机52个-AIOS
      // Sheet名：4.7-1
      const lastUnderscoreIndex = scenarioId.lastIndexOf('_')
      if (lastUnderscoreIndex > 0) {
        return scenarioId.substring(0, lastUnderscoreIndex)
      }
      return scenarioId
    },

    getSheetName(result) {
      if (!result || !result.meta || !result.meta.scenario_id) return '-'
      const scenarioId = result.meta.scenario_id
      // 场景ID格式: Excel文件名_Sheet名（从最后一个下划线拆分）
      const lastUnderscoreIndex = scenarioId.lastIndexOf('_')
      if (lastUnderscoreIndex > 0 && lastUnderscoreIndex < scenarioId.length - 1) {
        return scenarioId.substring(lastUnderscoreIndex + 1)
      }
      return '-'
    },

    get canLoadExcel() {
      // 检查是否可以加载Excel
      // 条件1: 不在加载中
      const notLoading = !this.loading
      
      // 条件2: 有alarmId（优先使用路由参数，然后是props，最后是result中的alarm_id）
      const routeAlarmId = this.$route?.params?.alarmId
      const propsAlarmId = this.alarmId
      const resultAlarmId = this.result?.alarm_id
      const hasAlarmId = !!(routeAlarmId || propsAlarmId || resultAlarmId)
      
      // 条件3: 有结果数据
      const hasResult = !!this.result
      
      const canLoad = notLoading && hasAlarmId && hasResult
      
      return canLoad
    },

    getExcelDisabledReason() {
      // 按优先级检查各个条件
      if (this.loading) {
        return '数据正在加载中，请稍候...'
      }
      if (!this.result) {
        return '结果数据未加载，无法加载Excel上下文'
      }
      const routeAlarmId = this.$route?.params?.alarmId
      const propsAlarmId = this.alarmId
      const resultAlarmId = this.result?.alarm_id
      if (!routeAlarmId && !propsAlarmId && !resultAlarmId) {
        return '缺少告警ID，无法加载Excel上下文'
      }
      // 如果所有基本条件都满足，按钮应该可用
      // 如果仍然禁用，可能是其他原因，但这种情况理论上不应该出现
      // 为了安全起见，提示用户检查配置
      return '请先配置Excel文件路径（在列表页点击"配置数据路径"按钮）'
    },

    async loadExcelContext() {
      // 使用alarmId（优先使用路由参数，然后是props，最后是result中的alarm_id）
      const targetAlarmId = this.$route?.params?.alarmId || this.alarmId || (this.result && this.result.alarm_id)
      
      if (!targetAlarmId) {
        this.$message.warning('缺少告警ID，无法加载Excel上下文')
        return
      }

      this.excelLoading = true
      this.excelError = null
      this.excelData = null

      try {
        const response = await axios.get(`/results/${targetAlarmId}/excel-context`)
        
        if (response.data.error) {
          this.excelError = response.data.error
          // 如果后端返回了详细信息，显示更友好的错误信息
          if (response.data.excel_file_name_expected) {
            let errorMsg = `未找到匹配的Excel文件。\n期望的文件名包含: ${response.data.excel_file_name_expected}\n\n可用文件数量: ${response.data.excel_files_count || 0}`
            if (response.data.excel_files_available && response.data.excel_files_available.length > 0) {
              errorMsg += `\n\n部分可用文件:\n${response.data.excel_files_available.slice(0, 5).join('\n')}`
            }
            this.excelError = errorMsg
          }
          this.$message.error('加载Excel上下文失败：' + response.data.error)
        } else if (response.data.data && response.data.data.length > 0) {
          this.excelData = response.data.data
          // 动态生成列定义
          this.generateExcelColumns(response.data.data)
          this.$message.success(`成功加载 ${response.data.total_rows} 行数据`)
        } else {
          this.excelError = 'Excel文件中没有数据'
          this.$message.warning('Excel文件中没有数据')
        }
      } catch (error) {
        console.error('加载Excel上下文失败:', error)
        const errorData = error.response?.data
        if (errorData && errorData.error) {
          this.excelError = errorData.error
          // 如果后端返回了详细信息，显示更友好的错误信息
          if (errorData.excel_file_name_expected) {
            let errorMsg = `未找到匹配的Excel文件。\n期望的文件名包含: ${errorData.excel_file_name_expected}\n\n可用文件数量: ${errorData.excel_files_count || 0}`
            if (errorData.excel_files_available && errorData.excel_files_available.length > 0) {
              errorMsg += `\n\n部分可用文件:\n${errorData.excel_files_available.slice(0, 5).join('\n')}`
            }
            this.excelError = errorMsg
          }
          this.$message.error('加载Excel上下文失败：' + errorData.error)
        } else {
          this.excelError = error.message || '加载失败，请检查网络连接或联系管理员'
          this.$message.error('加载Excel上下文失败：' + this.excelError)
        }
      } finally {
        this.excelLoading = false
      }
    },

    generateExcelColumns(data) {
      if (!data || data.length === 0) {
        this.excelColumns = []
        return
      }

      // 从第一行数据获取所有字段名
      const firstRow = data[0]
      this.excelColumns = Object.keys(firstRow).map(key => ({
        title: key,
        dataIndex: key,
        key: key,
        width: 150,
        ellipsis: true
      }))
    },

    retryLoad() {
      this.loadData()
    }
  }
}
</script>

<style scoped>
.detail {
  padding: 20px;
}

.back-button {
  margin-bottom: 16px;
}

.navigation {
  margin-bottom: 20px;
  text-align: center;
}

.page-info {
  font-weight: bold;
  color: #1890ff;
}

.meta-card {
  margin-bottom: 20px;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.meta-item .label {
  font-weight: bold;
  color: #666;
  font-size: 12px;
}

.prediction-tags {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}

.input-card {
  margin-bottom: 20px;
}

.content-text {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0;
  max-height: 300px;
  overflow-y: auto;
  background: #f6f8fa;
  padding: 12px;
  border-radius: 4px;
  border: 1px solid #e1e4e8;
}

.comparison-card {
  margin-bottom: 20px;
}

.comparison-section {
  margin-bottom: 20px;
}

.comparison-section h4 {
  margin-bottom: 12px;
  color: #1890ff;
}

.comparison-text {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
  background: #f6f8fa;
  padding: 12px;
  border-radius: 4px;
  border: 1px solid #e1e4e8;
  max-height: 400px;
  overflow-y: auto;
}

.excel-card {
  margin-bottom: 20px;
}

.excel-loading {
  text-align: center;
  padding: 40px;
}

.excel-error {
  margin-bottom: 16px;
}

.excel-table-container {
  margin-top: 16px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .detail {
    padding: 10px;
  }

  .comparison-card .ant-col {
    margin-bottom: 16px;
  }

  .comparison-card .ant-col:last-child {
    margin-bottom: 0;
  }
}
</style>

<template>
  <div class="home">
    <!-- 统计概览 -->
    <div class="stats-overview" v-if="stats">
      <a-row :gutter="16">
        <a-col :span="6">
          <a-statistic title="总样本数" :value="stats.total_results" />
        </a-col>
        <a-col :span="6">
          <a-statistic
            title="准确率"
            :value="stats.accuracy * 100"
            suffix="%"
            :precision="2"
          />
        </a-col>
        <a-col :span="6">
          <a-statistic
            title="F1分数"
            :value="stats.f1_score * 100"
            suffix="%"
            :precision="2"
          />
        </a-col>
        <a-col :span="6">
          <a-statistic title="解析失败" :value="stats.parse_failures" />
        </a-col>
      </a-row>
    </div>

    <!-- 筛选面板 -->
    <a-card class="filter-panel" title="筛选条件">
      <a-form layout="inline">
        <a-form-item label="搜索">
          <a-input
            v-model:value="searchInput"
            placeholder="搜索告警内容或输出..."
            @pressEnter="applyFilters"
            style="width: 200px"
          >
            <template #prefix>
              <SearchOutlined />
            </template>
          </a-input>
        </a-form-item>

        <a-form-item label="场景分类">
          <a-select
            v-model:value="categoryFilter"
            placeholder="选择场景分类"
            style="width: 150px"
            allowClear
            @change="applyFilters"
          >
            <a-select-option
              v-for="category in filterOptions?.categories"
              :key="category"
              :value="category"
            >
              {{ category }}
            </a-select-option>
          </a-select>
        </a-form-item>

        <a-form-item label="预测结果">
          <a-select
            v-model:value="correctnessFilter"
            placeholder="选择预测结果"
            style="width: 150px"
            allowClear
            @change="applyFilters"
          >
            <a-select-option value="correct">正确</a-select-option>
            <a-select-option value="incorrect">错误</a-select-option>
            <a-select-option value="parse_failed">解析失败</a-select-option>
          </a-select>
        </a-form-item>

        <a-form-item>
          <a-button type="primary" @click="applyFilters">
            筛选
          </a-button>
          <a-button @click="clearFilters" style="margin-left: 8px">
            清空
          </a-button>
        </a-form-item>
      </a-form>
    </a-card>

    <!-- 结果表格 -->
    <a-card class="results-table" title="评测结果列表">
      <a-table
        :columns="columns"
        :dataSource="results"
        :loading="loading"
        :pagination="tablePagination"
        @change="handleTableChange"
        :rowKey="(record, index) => record.alarm_id || `row-${index}`"
      >
        <template #bodyCell="{ column, record }">
          <!-- 告警ID列 -->
          <template v-if="column.key === 'alarm_id'">
            <a-typography-text copyable :copy-text="record.alarm_id" style="font-family: monospace; font-size: 12px;">
              {{ record.alarm_id }}
            </a-typography-text>
          </template>

          <!-- 告警内容列 -->
          <template v-if="column.key === 'alarm_content'">
            <div class="alarm-content">
              {{ getAlarmContent(record.input) }}
            </div>
          </template>

          <!-- 真实标签列 -->
          <template v-if="column.key === 'reference_label'">
            <a-tag :color="record.reference_label === 'convergent' ? 'green' : 'red'">
              {{ record.reference_label === 'convergent' ? '收敛' : '不收敛' }}
            </a-tag>
          </template>

          <!-- 正确性列 -->
          <template v-if="column.key === 'correctness'">
            <a-tag
              :color="record.correct ? 'green' : record.predicted_label === null ? 'orange' : 'red'"
            >
              {{ getCorrectnessText(record) }}
            </a-tag>
          </template>

          <!-- 场景分类列 -->
          <template v-if="column.key === 'category'">
            <a-tag color="blue">
              {{ record.meta?.category || '-' }}
            </a-tag>
          </template>

          <!-- Excel名称列 -->
          <template v-if="column.key === 'excel_name'">
            <a-tooltip :title="getExcelFileName(record)" placement="topLeft">
              <span style="font-size: 12px; color: #1890ff; display: inline-block; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                {{ getExcelFileName(record) }}
              </span>
            </a-tooltip>
          </template>

          <!-- Sheet名称列 -->
          <template v-if="column.key === 'sheet_name'">
            <a-tooltip :title="getSheetName(record)" placement="topLeft">
              <span style="font-size: 12px; color: #666; display: inline-block; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                {{ getSheetName(record) }}
              </span>
            </a-tooltip>
          </template>

          <!-- 操作列 -->
          <template v-if="column.key === 'actions'">
            <a-button
              type="link"
              size="small"
              @click="viewDetail(record.alarm_id)"
            >
              查看详情
            </a-button>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 空状态 -->
    <a-empty
      v-if="!hasData && !loading"
      description="暂无数据，请先上传评测结果文件"
    >
      <template #image>
        <UploadOutlined style="font-size: 64px; color: #d9d9d9;" />
      </template>
    </a-empty>
  </div>
</template>

<script>
import { SearchOutlined, UploadOutlined } from '@ant-design/icons-vue'
import { mapState, mapGetters, mapActions } from 'vuex'

export default {
  name: 'Home',
  components: {
    SearchOutlined,
    UploadOutlined
  },
  data() {
    return {
      searchInput: '',
      categoryFilter: null,
      correctnessFilter: null,
      columns: [
        {
          title: '告警ID',
          key: 'alarm_id',
          width: 150,
          ellipsis: true
        },
        {
          title: '告警内容',
          key: 'alarm_content',
          width: 250,
          ellipsis: true
        },
        {
          title: '真实标签',
          key: 'reference_label',
          width: 120,
          align: 'center'
        },
        {
          title: '正确性',
          key: 'correctness',
          width: 100,
          align: 'center'
        },
        {
          title: '场景分类',
          key: 'category',
          width: 120,
          align: 'center'
        },
        {
          title: 'Excel名称',
          key: 'excel_name',
          width: 180,
          ellipsis: true
        },
        {
          title: 'Sheet名称',
          key: 'sheet_name',
          width: 180,
          ellipsis: true
        },
        {
          title: '操作',
          key: 'actions',
          width: 100,
          align: 'center',
          fixed: 'right'
        }
      ]
    }
  },
  computed: {
    ...mapState('results', ['results', 'stats', 'filterOptions', 'loading']),
    ...mapState('filters', ['filters']),
    ...mapGetters('results', ['hasData']),

    tablePagination() {
      return {
        current: this.$store.state.results.pagination.page,
        pageSize: this.$store.state.results.pagination.size,
        total: this.$store.state.results.pagination.total,
        showSizeChanger: false,
        showQuickJumper: true,
        showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`
      }
    }
  },
  async created() {
    // 初始化数据
    await this.fetchFilterOptions()
    await this.fetchStats()
    await this.fetchResults(1)
  },
  methods: {
    ...mapActions('results', ['fetchResults', 'fetchStats', 'fetchFilterOptions']),
    ...mapActions('filters', ['updateFilter', 'clearFilters']),

    getAlarmContent(input) {
      // 从输入中提取告警内容
      const lines = input.split('\n')
      for (const line of lines) {
        if (line.startsWith('告警内容：')) {
          return line.replace('告警内容：', '').slice(0, 100) + (line.length > 100 ? '...' : '')
        }
      }
      return input.slice(0, 100) + '...'
    },

    getPredictionTagColor(record) {
      if (record.predicted_label === null) return 'orange'
      return record.correct ? 'green' : 'red'
    },

    getCorrectnessText(record) {
      if (record.predicted_label === null) return '解析失败'
      return record.correct ? '正确' : '错误'
    },

    getExcelFileName(record) {
      if (!record || !record.meta || !record.meta.scenario_id) return '-'
      const scenarioId = record.meta.scenario_id
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

    getSheetName(record) {
      if (!record || !record.meta || !record.meta.scenario_id) return '-'
      const scenarioId = record.meta.scenario_id
      // 场景ID格式: Excel文件名_Sheet名（从最后一个下划线拆分）
      const lastUnderscoreIndex = scenarioId.lastIndexOf('_')
      if (lastUnderscoreIndex > 0 && lastUnderscoreIndex < scenarioId.length - 1) {
        return scenarioId.substring(lastUnderscoreIndex + 1)
      }
      return '-'
    },


    applyFilters() {
      this.updateFilter({ key: 'search', value: this.searchInput })
      this.updateFilter({ key: 'category', value: this.categoryFilter })
      this.updateFilter({ key: 'correctness', value: this.correctnessFilter })
    },

    handleTableChange(pagination) {
      // 只处理分页
      if (pagination) {
        this.fetchResults(pagination.current)
      }
    },

    viewDetail(alarmId) {
      if (!alarmId) {
        this.$message.error('缺少告警ID，无法查看详情')
        return
      }
      this.$router.push({ name: 'Detail', params: { alarmId } })
    }
  }
}
</script>

<style scoped>
.home {
  padding: 20px;
}

.stats-overview {
  margin-bottom: 20px;
}

.filter-panel {
  margin-bottom: 20px;
}

.results-table {
  margin-bottom: 20px;
}

.alarm-content {
  max-width: 280px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .home {
    padding: 10px;
  }

  .stats-overview .ant-col {
    margin-bottom: 16px;
  }
}
</style>

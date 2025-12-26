import axios from 'axios'

export default {
  namespaced: true,

  state: {
    results: [], // 当前页的结果
    currentResult: null, // 当前详情结果
    stats: null, // 统计信息
    filterOptions: null, // 筛选选项
    pagination: {
      page: 1,
      size: 20,
      total: 0,
      pages: 0
    },
    loading: false,
    error: null
  },

  mutations: {
    SET_RESULTS(state, { results, pagination }) {
      state.results = results
      state.pagination = pagination
    },

    SET_CURRENT_RESULT(state, result) {
      state.currentResult = result
    },

    SET_STATS(state, stats) {
      state.stats = stats
    },

    SET_FILTER_OPTIONS(state, options) {
      state.filterOptions = options
    },

    SET_LOADING(state, loading) {
      state.loading = loading
    },

    SET_ERROR(state, error) {
      state.error = error
    },

    CLEAR_DATA(state) {
      state.results = []
      state.currentResult = null
      state.stats = null
      state.filterOptions = null
      state.pagination = {
        page: 1,
        size: 20,
        total: 0,
        pages: 0
      }
    }
  },

  actions: {
    async fetchResults({ commit, rootState }, page = 1) {
      commit('SET_LOADING', true)
      commit('SET_ERROR', null)

      try {
        const filters = rootState.filters.filters
        const params = {
          page,
          size: 20,
          ...filters
        }

        // 移除空的筛选参数
        Object.keys(params).forEach(key => {
          if (params[key] === null || params[key] === undefined || params[key] === '') {
            delete params[key]
          }
        })

        const response = await axios.get('/results', { params })

        const pagination = {
          page: response.data.pagination.page,
          size: response.data.pagination.size,
          total: response.data.pagination.total,
          pages: response.data.pagination.pages
        }

        commit('SET_RESULTS', {
          results: response.data.results,
          pagination
        })

      } catch (error) {
        console.error('获取结果失败:', error)
        commit('SET_ERROR', error.response?.data?.detail || error.message)
      } finally {
        commit('SET_LOADING', false)
      }
    },

    async fetchResultDetail({ commit }, alarmId) {
      commit('SET_LOADING', true)
      commit('SET_ERROR', null)

      try {
        const response = await axios.get(`/results/${alarmId}`)
        commit('SET_CURRENT_RESULT', response.data)
      } catch (error) {
        console.error('获取结果详情失败:', error)
        commit('SET_ERROR', error.response?.data?.detail || error.message)
      } finally {
        commit('SET_LOADING', false)
      }
    },

    async fetchStats({ commit }) {
      try {
        const response = await axios.get('/stats/overview')
        commit('SET_STATS', response.data)
      } catch (error) {
        console.error('获取统计信息失败:', error)
        commit('SET_ERROR', error.response?.data?.detail || error.message)
      }
    },

    async fetchFilterOptions({ commit }) {
      try {
        const response = await axios.get('/filters/options')
        commit('SET_FILTER_OPTIONS', response.data)
      } catch (error) {
        console.error('获取筛选选项失败:', error)
        commit('SET_ERROR', error.response?.data?.detail || error.message)
      }
    },

    async clearData({ commit }) {
      try {
        await axios.delete('/data')
        commit('CLEAR_DATA')
      } catch (error) {
        console.error('清除数据失败:', error)
        commit('SET_ERROR', error.response?.data?.detail || error.message)
      }
    }
  },

  getters: {
    hasData: state => state.results.length > 0 || state.currentResult !== null,
    currentPage: state => state.pagination.page,
    totalPages: state => state.pagination.pages,
    totalResults: state => state.pagination.total
  }
}

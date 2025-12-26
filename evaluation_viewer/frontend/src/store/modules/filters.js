export default {
  namespaced: true,

  state: {
    filters: {
      search: '',
      category: null,
      correctness: null,
      scenario_id: null,
      reference_label: null,
      alarm_id: null,
      excel_name: null,
      sheet_name: null
    }
  },

  mutations: {
    SET_FILTER(state, { key, value }) {
      state.filters[key] = value
    },

    SET_FILTERS(state, filters) {
      state.filters = { ...filters }
    },

    CLEAR_FILTERS(state) {
      state.filters = {
        search: '',
        category: null,
        correctness: null,
        scenario_id: null,
        reference_label: null,
        alarm_id: null,
        excel_name: null,
        sheet_name: null
      }
    }
  },

  actions: {
    updateFilter({ commit, dispatch }, { key, value }) {
      commit('SET_FILTER', { key, value })
      // 筛选条件改变时，重新获取结果（第一页）
      dispatch('results/fetchResults', 1, { root: true })
    },

    setFilters({ commit, dispatch }, filters) {
      commit('SET_FILTERS', filters)
      // 设置多个筛选条件后，重新获取结果
      dispatch('results/fetchResults', 1, { root: true })
    },

    clearFilters({ commit, dispatch }) {
      commit('CLEAR_FILTERS')
      // 清除筛选条件后，重新获取结果
      dispatch('results/fetchResults', 1, { root: true })
    }
  },

  getters: {
    activeFiltersCount: state => {
      let count = 0
      if (state.filters.search) count++
      if (state.filters.category) count++
      if (state.filters.correctness) count++
      if (state.filters.scenario_id) count++
      if (state.filters.reference_label) count++
      if (state.filters.alarm_id) count++
      if (state.filters.excel_name) count++
      if (state.filters.sheet_name) count++
      return count
    },

    hasActiveFilters: (state, getters) => getters.activeFiltersCount > 0
  }
}

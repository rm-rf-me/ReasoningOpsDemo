import { createStore } from 'vuex'
import results from './modules/results'
import filters from './modules/filters'

export default createStore({
  modules: {
    results,
    filters
  }
})

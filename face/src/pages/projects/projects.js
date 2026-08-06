const { request, getCustomerToken } = require('../../utils/request')
const { formatDate } = require('../../utils/util')

const PAGE_SIZE = 10

Page({
  data: {
    list: [],
    page: 1,
    hasMore: true,
    loading: false,
    error: '',
    needLogin: false,
    noCompany: false,
  },

  onShow() {
    const app = getApp()
    if (!app.globalData.currentCompanyId) {
      this.setData({ noCompany: true, needLogin: false, list: [] })
      return
    }
    if (!getCustomerToken()) {
      this.setData({ needLogin: true, noCompany: false, list: [] })
      return
    }
    this.setData({ needLogin: false, noCompany: false })
    this.loadList(true)
  },

  onPullDownRefresh() {
    this.onShow().finally(() => wx.stopPullDownRefresh())
  },

  onReachBottom() {
    if (this.data.hasMore && !this.data.loading) {
      this.loadList(false)
    }
  },

  async loadList(reset) {
    const companyId = getApp().globalData.currentCompanyId
    if (!companyId) return
    if (this.data.loading) return
    const page = reset ? 1 : this.data.page + 1
    this.setData({ loading: true, error: '' })
    try {
      const data = await request(`/customer/projects/?company=${companyId}&page=${page}&page_size=${PAGE_SIZE}`)
      const items = (data.results || []).map((item) => ({
        ...item,
        createdText: formatDate(item.created_at),
      }))
      this.setData({
        list: reset ? items : this.data.list.concat(items),
        page,
        hasMore: !!data.next,
        loading: false,
      })
    } catch (err) {
      this.setData({
        loading: false,
        error: err.message,
        list: reset ? [] : this.data.list,
      })
    }
  },

  goDetail(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/project-detail/project-detail?id=${id}` })
  },

  goLogin() {
    getApp().globalData.afterLogin = '/pages/projects/projects'
    wx.navigateTo({ url: '/pages/login/login' })
  },

  goIndex() {
    wx.reLaunch({ url: '/pages/index/index' })
  },
})

const { request } = require('../../utils/request')
const { absUrl, formatDate, formatBudget } = require('../../utils/util')

const PAGE_SIZE = 10

Page({
  data: {
    list: [],
    page: 1,
    hasMore: true,
    loading: false,
    error: '',
    noCompany: false,
  },

  onShow() {
    if (!getApp().globalData.currentCompanyId) {
      this.setData({ noCompany: true, list: [] })
      return
    }
    this.setData({ noCompany: false })
    this.loadList(true)
  },

  onPullDownRefresh() {
    this.loadList(true).finally(() => wx.stopPullDownRefresh())
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
      const data = await request(`/public/cases/?company=${companyId}&page=${page}&page_size=${PAGE_SIZE}`)
      const items = (data.results || []).map((item) => ({
        ...item,
        cover: absUrl(item.cover),
        budgetText: formatBudget(item.budget),
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
    wx.navigateTo({ url: `/pages/case-detail/case-detail?id=${id}` })
  },

  goIndex() {
    wx.reLaunch({ url: '/pages/index/index' })
  },
})

const { request } = require('../../utils/request')
const { absUrl, formatDate, initial } = require('../../utils/util')

Page({
  data: {
    company: null,
    loading: true,
    error: '',
  },

  onShow() {
    this.loadCompany()
  },

  onPullDownRefresh() {
    this.loadCompany().finally(() => wx.stopPullDownRefresh())
  },

  async loadCompany() {
    this.setData({ loading: true, error: '' })
    try {
      // 公司管理员只能看到自己的公司，超级管理员取第一条
      const data = await request('/companies/')
      const item = data.results && data.results.length ? data.results[0] : null
      if (!item) {
        this.setData({ company: null, loading: false })
        return
      }
      this.setData({
        company: {
          ...item,
          logo: absUrl(item.logo),
          logoText: initial(item.name),
          createdText: formatDate(item.created_at),
          active: item.status === 'active',
        },
        loading: false,
      })
    } catch (err) {
      this.setData({ loading: false, error: err.message })
    }
  },

  callPhone(e) {
    const phone = e.currentTarget.dataset.phone
    if (!phone) return
    wx.makePhoneCall({ phoneNumber: String(phone) })
  },
})

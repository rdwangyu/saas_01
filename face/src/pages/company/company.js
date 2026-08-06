const { request } = require('../../utils/request')
const { absUrl, formatDate, initial } = require('../../utils/util')

Page({
  data: {
    company: null,
    loading: true,
    error: '',
    noCompany: false,
  },

  onShow() {
    const id = getApp().globalData.currentCompanyId
    if (!id) {
      this.setData({ company: null, loading: false, noCompany: true, error: '' })
      return
    }
    this.loadCompany()
  },

  onPullDownRefresh() {
    this.loadCompany().finally(() => wx.stopPullDownRefresh())
  },

  async loadCompany() {
    const id = getApp().globalData.currentCompanyId
    if (!id) return
    this.setData({ loading: true, error: '', noCompany: false })
    try {
      const item = await request(`/public/companies/${id}/`)
      this.setData({
        company: {
          ...item,
          logo: absUrl(item.logo),
          logoText: initial(item.name),
          establishedText: item.established_date ? formatDate(item.established_date) : '',
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

  goIndex() {
    wx.reLaunch({ url: '/pages/index/index' })
  },
})

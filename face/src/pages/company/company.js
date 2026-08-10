const { request } = require('../../utils/request')
const { absUrl, formatDate, initial } = require('../../utils/util')

Page({
  data: {
    company: null,
    loading: true,
    error: '',
  },

  onShow() {
    const id = getApp().getCurrentCompanyId()
    if (!id) {
      this.setData({ company: null, loading: false, error: '' })
      return
    }
    this.loadCompany()
  },

  onPullDownRefresh() {
    this.loadCompany().finally(() => wx.stopPullDownRefresh())
  },

  async loadCompany() {
    const id = getApp().getCurrentCompanyId()
    if (!id) return
    this.setData({ loading: true, error: '' })
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
})

const { request } = require('../../utils/request')

Page({
  data: {
    companyId: '',
    loading: false,
  },

  onInput(e) {
    this.setData({ companyId: e.detail.value })
  },

  async onEnter() {
    const id = this.data.companyId.trim()
    if (!id) {
      wx.showToast({ title: '请输入公司ID', icon: 'none' })
      return
    }
    if (!/^\d+$/.test(id)) {
      wx.showToast({ title: '公司ID为数字', icon: 'none' })
      return
    }
    this.setData({ loading: true })
    try {
      // 校验公司存在后再进入
      await request(`/public/companies/${id}/`)
      getApp().setCompany(Number(id))
      wx.switchTab({ url: '/pages/company/company' })
    } catch (err) {
      wx.showToast({ title: err.message || '公司不存在，请核对ID', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },
})

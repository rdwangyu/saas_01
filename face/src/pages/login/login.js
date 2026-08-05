const { request, setTokens } = require('../../utils/request')

Page({
  data: {
    username: '',
    password: '',
    loading: false,
  },

  onInput(e) {
    const field = e.currentTarget.dataset.field
    this.setData({ [field]: e.detail.value })
  },

  async onLogin() {
    const { username, password } = this.data
    if (!username.trim()) {
      wx.showToast({ title: '请输入用户名', icon: 'none' })
      return
    }
    if (!password) {
      wx.showToast({ title: '请输入密码', icon: 'none' })
      return
    }
    this.setData({ loading: true })
    try {
      const data = await request('/auth/login/', {
        method: 'POST',
        data: { username: username.trim(), password },
      })
      setTokens(data.access, data.refresh)
      const me = await request('/me/')
      getApp().globalData.userInfo = me
      wx.showToast({ title: '登录成功', icon: 'success' })
      setTimeout(() => {
        wx.switchTab({ url: '/pages/company/company' })
      }, 500)
    } catch (err) {
      wx.showToast({ title: err.message || '登录失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },
})

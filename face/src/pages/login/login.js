const { request, setCustomerToken } = require('../../utils/request')

Page({
  data: {
    phone: '',
    code: '',
    loading: false,
    sending: false,
    countdown: 0,
  },

  onInput(e) {
    this.setData({ [e.currentTarget.dataset.field]: e.detail.value })
  },

  onUnload() {
    if (this._timer) clearInterval(this._timer)
  },

  /** 发送验证码 */
  async onSendCode() {
    const phone = this.data.phone.trim()
    if (!/^1\d{10}$/.test(phone)) {
      wx.showToast({ title: '请输入正确的手机号', icon: 'none' })
      return
    }
    this.setData({ sending: true })
    try {
      await request('/customer/send-code/', { method: 'POST', data: { phone } })
      wx.showToast({ title: '验证码已发送', icon: 'success' })
      this.startCountdown()
    } catch (err) {
      wx.showToast({ title: err.message || '发送失败', icon: 'none' })
    } finally {
      this.setData({ sending: false })
    }
  },

  startCountdown() {
    let n = 60
    this.setData({ countdown: n })
    this._timer = setInterval(() => {
      n -= 1
      if (n <= 0) {
        clearInterval(this._timer)
        this.setData({ countdown: 0 })
      } else {
        this.setData({ countdown: n })
      }
    }, 1000)
  },

  /** 手机号 + 验证码 登录 */
  async onLogin() {
    const phone = this.data.phone.trim()
    const code = this.data.code.trim()
    if (!/^1\d{10}$/.test(phone)) {
      wx.showToast({ title: '请输入正确的手机号', icon: 'none' })
      return
    }
    if (!code) {
      wx.showToast({ title: '请输入验证码', icon: 'none' })
      return
    }
    this.setData({ loading: true })
    try {
      const data = await request('/customer/login/', {
        method: 'POST',
        data: { phone, code },
      })
      setCustomerToken(data.token)
      getApp().globalData.userInfo = data.customer
      wx.showToast({ title: '登录成功', icon: 'success' })
      const target = getApp().globalData.afterLogin || '/pages/projects/projects'
      setTimeout(() => wx.switchTab({ url: target }), 400)
    } catch (err) {
      wx.showToast({ title: err.message || '登录失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },
})

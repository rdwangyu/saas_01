const { request, getCustomerToken, clearCustomerToken } = require('../../utils/request')
const { initial } = require('../../utils/util')

Page({
  data: {
    me: null,
    needLogin: false,
  },

  onShow() {
    if (!getCustomerToken()) {
      this.setData({ needLogin: true, me: null })
      return
    }
    this.setData({ needLogin: false })
    this.loadMe()
  },

  onPullDownRefresh() {
    this.onShow().finally(() => wx.stopPullDownRefresh())
  },

  async loadMe() {
    const app = getApp()
    try {
      const me = await request('/customer/me/')
      this.setData({
        me: {
          ...me,
          initial: initial(me.name),
        },
      })
      app.globalData.userInfo = me
    } catch (err) {
      // 401 时 request 内部已清除客户 token，此处刷新为未登录态
      if (err.statusCode === 401) {
        this.setData({ needLogin: true, me: null })
      }
    }
  },

  goLogin() {
    getApp().globalData.afterLogin = '/pages/users/users'
    wx.navigateTo({ url: '/pages/login/login' })
  },

  /** 切换公司：回到首页重新输入公司 ID */
  switchCompany() {
    wx.showModal({
      title: '切换公司',
      content: '确定要切换公司吗？切换后将以新公司的视角查看。',
      success: (res) => {
        if (!res.confirm) return
        wx.reLaunch({ url: '/pages/index/index' })
      },
    })
  },

  /** 退出登录：清除客户 token，停留在本页并切换为未登录态（不跳首页） */
  onLogout() {
    wx.showModal({
      title: '退出登录',
      content: '确定要退出当前账号吗？',
      confirmColor: '#f43f5e',
      success: (res) => {
        if (!res.confirm) return
        clearCustomerToken()
        getApp().globalData.userInfo = null
        this.onShow()
      },
    })
  },
})

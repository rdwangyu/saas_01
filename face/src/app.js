const { getToken } = require('./utils/request')

App({
  globalData: {
    // 当前登录用户信息（登录成功后写入）
    userInfo: null,
  },

  onLaunch() {
    // 已登录则直接进入首页（公司简介），否则停留在登录页
    if (getToken()) {
      wx.switchTab({ url: '/pages/company/company' })
    }
  },
})

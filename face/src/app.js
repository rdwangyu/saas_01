const COMPANY_KEY = 'company_id'

App({
  globalData: {
    // 当前进入的公司 id（索引页输入后写入）
    currentCompanyId: null,
    // 当前登录客户信息（登录成功后写入）
    userInfo: null,
    // 登录成功后要跳转的 tab 页（项目进度/我的）
    afterLogin: null,
  },

  onLaunch() {
    // 恢复上次进入的公司
    this.globalData.currentCompanyId = wx.getStorageSync(COMPANY_KEY) || null
  },

  // 进入公司：保存 id 并写入缓存
  setCompany(id) {
    this.globalData.currentCompanyId = id
    wx.setStorageSync(COMPANY_KEY, id)
  },
})

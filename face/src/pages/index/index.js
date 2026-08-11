Page({
  onShow() {
    // 已有公司（通过分享/扫码进入过）→ 直接进公司 tab
    if (getApp().getCurrentCompanyId()) {
      wx.switchTab({ url: '/pages/company/company' })
    }
  },

  /** 扫码进入公司（支持相册选择二维码图片） */
  async scanCompany() {
    const ok = await getApp().scanCompany()
    if (ok) {
      wx.switchTab({ url: '/pages/company/company' })
    }
  },
})

Page({
  data: {
    user: {
      name: '张先生',
      community: '云璟府',
      building: '3幢',
      unit: '1202室'
    }
  },

  onContract() {
    wx.showToast({ title: '合同文件', icon: 'none' })
  }
})

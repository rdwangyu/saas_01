const { absUrl, formatDate, formatDateTime } = require('../../utils/util')

Page({
  data: {
    detail: null,
    error: '',
  },

  onShow() {
    const project = getApp().globalData.boundProject
    if (!project) {
      this.setData({ error: '请先绑定订单', detail: null })
      return
    }
    const stages = (project.stages || []).map((stage) => ({
      ...stage,
      images: [stage.image_0, stage.image_1, stage.image_2].filter(Boolean).map(absUrl),
      updatedText: formatDateTime(stage.updated_at),
    }))
    this.setData({
      detail: { ...project, createdText: formatDate(project.created_at), stages },
      error: '',
    })
  },

  callPhone(e) {
    const phone = e.currentTarget.dataset.phone
    if (!phone) return
    wx.makePhoneCall({ phoneNumber: String(phone) })
  },

  previewStage(e) {
    const { index, img } = e.currentTarget.dataset
    const stage = this.data.detail.stages[index]
    if (!stage || !stage.images.length) return
    wx.previewImage({ urls: stage.images, current: img })
  },

  goBind() {
    wx.switchTab({ url: '/pages/projects/projects' })
  },
})

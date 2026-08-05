const { request } = require('../../utils/request')
const { absUrl, formatDate, formatDateTime } = require('../../utils/util')

Page({
  data: {
    id: null,
    detail: null,
    error: '',
  },

  onLoad(options) {
    this.setData({ id: options.id })
    this.loadDetail()
  },

  async loadDetail() {
    try {
      const detail = await request(`/projects/${this.data.id}/`)
      const stages = (detail.stages || []).map((stage) => ({
        ...stage,
        images: [stage.image_0, stage.image_1, stage.image_2]
          .filter(Boolean)
          .map(absUrl),
        updatedText: formatDateTime(stage.updated_at),
      }))
      this.setData({
        detail: {
          ...detail,
          createdText: formatDate(detail.created_at),
          stages,
        },
        error: '',
      })
    } catch (err) {
      this.setData({ error: err.message })
    }
  },

  goBack() {
    wx.navigateBack()
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
})

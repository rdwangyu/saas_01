const { request } = require('../../utils/request')
const { absUrl, formatDate, formatBudget } = require('../../utils/util')

Page({
  data: {
    id: null,
    detail: null,
    images: [],
    error: '',
  },

  onLoad(options) {
    this.setData({ id: options.id })
    this.loadDetail()
  },

  async loadDetail() {
    try {
      const detail = await request(`/public/cases/${this.data.id}/`)
      const images = []
      if (detail.cover) images.push(absUrl(detail.cover))
      ;(detail.images || []).forEach((url) => {
        const abs = absUrl(url)
        if (images.indexOf(abs) === -1) images.push(abs)
      })
      this.setData({
        detail: {
          ...detail,
          cover: absUrl(detail.cover),
          images: (detail.images || []).map(absUrl),
          video: absUrl(detail.video),
          budgetText: formatBudget(detail.budget),
          createdText: formatDate(detail.created_at),
        },
        images,
        error: '',
      })
    } catch (err) {
      this.setData({ error: err.message })
    }
  },

  goBack() {
    wx.navigateBack()
  },

  previewImage(e) {
    const current = e.currentTarget.dataset.current
    wx.previewImage({ urls: this.data.images, current })
  },
})

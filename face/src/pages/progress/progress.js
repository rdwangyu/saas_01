const app = getApp()

Page({
  data: {
    project: null,
    percent: 0
  },

  onLoad() {
    const p = app.globalData.project
    const percent = Math.round(p.currentStage / p.stages.length * 100)
    this.setData({ project: p, percent })
  },

  previewImage(e) {
    const src = e.currentTarget.dataset.src
    wx.previewImage({
      urls: app.globalData.project.photos,
      current: src
    })
  }
})

const app = getApp()

Page({
  data: {
    cases: [],
    playingVideo: null
  },

  onLoad() {
    this.setData({ cases: app.globalData.cases || [] })
  },

  playVideo(e) {
    const id = e.currentTarget.dataset.id
    const c = this.data.cases.find(x => x.id === id)
    if (!c || !c.video) return
    this.setData({ playingVideo: c })
  },

  closeVideo() {
    this.setData({ playingVideo: null })
  }
})

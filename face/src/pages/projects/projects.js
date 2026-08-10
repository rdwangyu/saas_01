const { request } = require('../../utils/request')
const { formatDate } = require('../../utils/util')

Page({
  data: {
    bound: false,
    project: null,
    loading: false,
    error: '',
  },

  onShow() {
    const app = getApp()
    if (!app.globalData.orderNo) {
      this.setData({ bound: false, project: null, error: '' })
      return
    }
    this.loadProject()
  },

  onPullDownRefresh() {
    this.loadProject().finally(() => wx.stopPullDownRefresh())
  },

  /** 拉取绑定项目最新进度（同时刷新缓存） */
  async loadProject() {
    const app = getApp()
    if (!app.globalData.orderNo) return
    this.setData({ loading: true, error: '' })
    try {
      const project = await request('/bind-project/', {
        method: 'POST',
        data: { project_no: app.globalData.orderNo },
      })
      app.setBound(app.globalData.orderNo, project.company, project)
      this.setData({
        bound: true,
        project: { ...project, createdText: formatDate(project.created_at) },
        loading: false,
      })
    } catch (err) {
      // 编号失效（项目被删/停用）→ 自动解绑
      if (err.statusCode === 400) {
        app.clearBound()
        this.setData({ bound: false, project: null, loading: false })
      } else {
        this.setData({ bound: true, loading: false, error: err.message })
      }
    }
  },

  async bindOrder() {
    const ok = await getApp().bindOrder()
    if (ok) this.onShow()
  },

  goDetail() {
    wx.navigateTo({ url: '/pages/project-detail/project-detail' })
  },
})

const { request } = require('../../utils/request')
const { absUrl, formatDate, formatDateTime } = require('../../utils/util')

/** 组装详情数据：图片地址转完整 URL，日期格式化 */
function buildDetail(project) {
  const stages = (project.stages || []).map((stage) => ({
    ...stage,
    images: [stage.image_0, stage.image_1, stage.image_2].filter(Boolean).map(absUrl),
    updatedText: formatDateTime(stage.updated_at),
  }))
  return { ...project, createdText: formatDate(project.created_at), stages }
}

Page({
  data: {
    bound: false,
    detail: null,
    loading: false,
    error: '',
  },

  onShow() {
    const app = getApp()
    if (!app.globalData.orderNo) {
      this.setData({ bound: false, detail: null, error: '' })
      return
    }
    // 防御：绑定项目必须属于当前查看的公司，否则解绑，绝不展示其他公司的项目
    const project = app.globalData.boundProject
    const companyId = app.getCurrentCompanyId()
    if (project && companyId && project.company !== companyId) {
      app.clearBound()
      this.setData({ bound: false, detail: null, error: '' })
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
        data: {
          project_no: app.globalData.orderNo,
          company: app.getCurrentCompanyId(),
        },
      })
      app.setBound(app.globalData.orderNo, project.company, project)
      this.setData({
        bound: true,
        detail: buildDetail(project),
        loading: false,
      })
    } catch (err) {
      // 编号失效（项目被删/停用）→ 自动解绑
      if (err.statusCode === 400) {
        app.clearBound()
        this.setData({ bound: false, detail: null, loading: false })
      } else {
        this.setData({ bound: true, loading: false, error: err.message })
      }
    }
  },

  async bindOrder() {
    const ok = await getApp().bindOrder()
    if (ok) this.onShow()
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

const VIEW_COMPANY_KEY = 'company_id' // 当前查看的公司（扫码进入后保存）
const ORDER_KEY = 'order_no' // 绑定的订单编号
const BOUND_COMPANY_KEY = 'bound_company_id' // 绑定订单所属公司 id

const { request } = require('./utils/request')

/** 从扫码结果/场景参数里提取公司 id：支持 URL、companyId=3、company_3、纯数字等 */
function parseCompanyId(raw) {
  const text = String(raw || '').trim()
  if (!text) return null
  const patterns = [
    /\/public\/companies\/(\d+)/,
    /\/companies\/(\d+)/,
    /company[=_:]?id[=:]?(\d+)/i,
    /company[=_:](\d+)/i,
    /[?&]id[=:](\d+)/,
    /(\d+)$/,
  ]
  for (const p of patterns) {
    const m = text.match(p)
    if (m) return Number(m[1])
  }
  return null
}

App({
  globalData: {
    companyId: null, // 当前查看的公司 id（扫码进入）
    orderNo: null, // 当前绑定订单编号
    boundCompanyId: null, // 绑定订单所属公司 id
    boundProject: null, // 绑定项目数据
  },

  onLaunch(options) {
    // 恢复本地状态
    this.globalData.companyId = wx.getStorageSync(VIEW_COMPANY_KEY) || null
    this.globalData.orderNo = wx.getStorageSync(ORDER_KEY) || null
    this.globalData.boundCompanyId = wx.getStorageSync(BOUND_COMPANY_KEY) || null
    this._processEntryOptions(options)
  },

  // 小程序已运行再点分享/扫码进入时，onShow 也会带 options，同样处理
  onShow(options) {
    this._processEntryOptions(options)
  },

  /**
   * 处理进入参数里的公司 id（扫码/分享/小程序码）。
   * 注意 options.scene 是场景码数字（如 1047=扫小程序码），不是业务内容；
   * 业务内容在 options.q（扫码）或 options.query（分享卡片/页面 query）里。
   */
  _processEntryOptions(options) {
    if (!options) return
    const q = options.q ? decodeURIComponent(options.q) : ''
    const query = options.query
    let sceneStr = ''
    let companyIdStr = ''
    if (typeof query === 'string') {
      sceneStr = query
    } else if (query) {
      if (query.scene) sceneStr = String(query.scene)
      companyIdStr = String(query.company_id || query.companyId || '')
    }
    const id = parseCompanyId(q) || parseCompanyId(sceneStr) || parseCompanyId(companyIdStr)
    if (id) this.setCompanyId(id)
  },

  /** 当前应展示的公司 id：优先扫码/分享选中的公司，其次绑定订单所属公司 */
  getCurrentCompanyId() {
    return this.globalData.companyId || this.globalData.boundCompanyId
  },

  /** 扫码进入公司：扫描二维码/小程序码 → 解析公司 id → 校验 → 存本地 */
  scanCompany() {
    return new Promise((resolve) => {
      wx.scanCode({
        onlyFromCamera: false,
        success: async (res) => {
          // 普通二维码内容在 res.result；小程序码内容在 res.path（pages/...?scene=company_2）
          const id = parseCompanyId(res.result) || parseCompanyId(res.path)
          if (!id) {
            wx.showToast({ title: '二维码无效，未识别公司', icon: 'none' })
            return resolve(false)
          }
          try {
            await request(`/public/companies/${id}/`)
            this.setCompanyId(id)
            wx.showToast({ title: '已进入公司', icon: 'success' })
            resolve(true)
          } catch (err) {
            wx.showToast({ title: err.message || '公司不存在', icon: 'none' })
            resolve(false)
          }
        },
        fail: () => resolve(false),
      })
    })
  },

  /** 保存当前查看的公司 */
  setCompanyId(id) {
    this.globalData.companyId = id
    wx.setStorageSync(VIEW_COMPANY_KEY, id)
    // 防跨公司串数据：若已绑定的订单属于其他公司，进入新公司时自动解绑，
    // 项目进度/“我的”回到“未绑定订单”，绝不展示别的公司的项目。
    if (this.globalData.boundCompanyId && this.globalData.boundCompanyId !== id) {
      this.clearBound()
    }
  },

  /** 绑定订单：弹窗输入订单编号 → 后端校验（仅限当前公司）→ 成功写入全局 + 缓存 */
  bindOrder() {
    return new Promise((resolve) => {
      const companyId = this.getCurrentCompanyId()
      if (!companyId) {
        wx.showToast({ title: '请先扫码进入公司', icon: 'none' })
        return resolve(false)
      }
      wx.showModal({
        title: '绑定订单',
        editable: true,
        placeholderText: '请输入订单编号',
        success: async (res) => {
          if (!res.confirm) return resolve(false)
          const orderNo = (res.content || '').trim()
          if (!orderNo) {
            wx.showToast({ title: '请输入订单编号', icon: 'none' })
            return resolve(false)
          }
          try {
            const project = await request('/bind-project/', {
              method: 'POST',
              data: { project_no: orderNo, company: companyId },
            })
            this.setBound(orderNo, project.company, project)
            wx.showToast({ title: '绑定成功', icon: 'success' })
            resolve(true)
          } catch (err) {
            wx.showToast({ title: err.message || '订单编号不正确', icon: 'none' })
            resolve(false)
          }
        },
        fail: () => resolve(false),
      })
    })
  },

  /** 写入绑定状态 */
  setBound(orderNo, companyId, project) {
    this.globalData.orderNo = orderNo
    this.globalData.boundCompanyId = companyId
    this.globalData.boundProject = project
    wx.setStorageSync(ORDER_KEY, orderNo)
    wx.setStorageSync(BOUND_COMPANY_KEY, companyId)
  },

  /** 解绑订单：只清订单相关，保留已查看的公司 */
  clearBound() {
    this.globalData.orderNo = null
    this.globalData.boundCompanyId = null
    this.globalData.boundProject = null
    wx.removeStorageSync(ORDER_KEY)
    wx.removeStorageSync(BOUND_COMPANY_KEY)
  },
})

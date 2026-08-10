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
    // 扫码/小程序码进入：options.scene 是场景码数字（如 1047=扫小程序码），不能当公司 id 用。
    // scene 业务内容在 options.q（扫码）或 options.query（编译参数/页面 query）里。
    const q = options && options.q ? decodeURIComponent(options.q) : ''
    const query = options && options.query
    let queryScene = ''
    if (typeof query === 'string') queryScene = query
    else if (query && query.scene) queryScene = String(query.scene)
    const id = parseCompanyId(q) || parseCompanyId(queryScene)
    if (id) this.setCompanyId(id)
  },

  /** 当前应展示的公司 id：优先扫码选中的公司，其次绑定订单所属公司 */
  getCurrentCompanyId() {
    return this.globalData.companyId || this.globalData.boundCompanyId
  },

  /** 扫码进入公司：扫描二维码 → 解析公司 id → 校验 → 存本地 */
  scanCompany() {
    return new Promise((resolve) => {
      wx.scanCode({
        onlyFromCamera: false,
        success: async (res) => {
          const id = parseCompanyId(res.result)
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
  },

  /** 绑定订单：弹窗输入订单编号 → 后端校验 → 成功写入全局 + 缓存 */
  bindOrder() {
    return new Promise((resolve) => {
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
              data: { project_no: orderNo },
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

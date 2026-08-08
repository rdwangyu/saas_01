/**
 * 网络请求封装
 * - 客户（手机号+验证码）登录后使用 customer_token，Bearer 携带
 * - 公开接口（公司/案例）免登录，不携带 token
 * - 客户 token 失效（401）时清除登录态，由页面展示“请先登录”（不自动跳登录页）
 */
const { BASE_URL } = require('../config')

const CUSTOMER_TOKEN_KEY = 'customer_token'

/* ---------- 客户 token ---------- */
function getCustomerToken() {
  return wx.getStorageSync(CUSTOMER_TOKEN_KEY) || ''
}

function setCustomerToken(token) {
  wx.setStorageSync(CUSTOMER_TOKEN_KEY, token)
}

function clearCustomerToken() {
  wx.removeStorageSync(CUSTOMER_TOKEN_KEY)
}

/**
 * 从 DRF 错误响应中提取可读的错误信息
 * 支持 {detail: "..."} 与 {field: ["msg1", ...]} 两种格式
 */
function extractError(data) {
  if (!data) return '请求失败，请稍后重试'
  if (typeof data === 'string') return data
  if (data.detail) {
    return typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
  }
  for (const key in data) {
    const v = data[key]
    if (Array.isArray(v) && v.length) return String(v[0])
    if (typeof v === 'string') return v
  }
  return '请求失败，请稍后重试'
}

/** 底层请求，不做 401 处理 */
function rawRequest(url, method, data) {
  return new Promise((resolve, reject) => {
    const header = { 'Content-Type': 'application/json' }
    const token = getCustomerToken()
    if (token) header.Authorization = `Bearer ${token}`
    wx.request({
      url: BASE_URL + url,
      method,
      data,
      header,
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          const err = new Error(extractError(res.data))
          err.statusCode = res.statusCode
          reject(err)
        }
      },
      fail() {
        reject(new Error('网络连接失败，请检查网络或后端服务'))
      },
    })
  })
}

/**
 * 统一请求入口
 * @param {string} url 接口路径，如 '/public/cases/'
 * @param {object} options { method, data }
 */
function request(url, options = {}) {
  const { method = 'GET', data = {} } = options
  return rawRequest(url, method, data).catch((err) => {
    // 客户 token 失效：清除登录态，由页面展示“请先登录”
    if (err.statusCode === 401 && getCustomerToken()) {
      clearCustomerToken()
      getApp().globalData.userInfo = null
    }
    throw err
  })
}

module.exports = {
  request,
  getCustomerToken,
  setCustomerToken,
  clearCustomerToken,
  extractError,
}

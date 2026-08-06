/**
 * 网络请求封装
 * - 客户（手机号+验证码）登录后使用 customer_token，Bearer 携带
 * - 公开接口（公司/案例）免登录，不携带 token
 * - 客户 token 失效时不自动刷新，由页面提示“请先登录”
 * - 保留旧的员工 JWT 刷新逻辑（兼容历史数据，小程序已不再使用员工登录）
 */
const { BASE_URL } = require('../config')

const TOKEN_KEY = 'access_token'
const REFRESH_KEY = 'refresh_token'
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

/* ---------- 旧员工 JWT（兼容保留） ---------- */
function getToken() {
  return getCustomerToken() || wx.getStorageSync(TOKEN_KEY) || ''
}

function getRefreshToken() {
  return wx.getStorageSync(REFRESH_KEY) || ''
}

function setTokens(access, refresh) {
  wx.setStorageSync(TOKEN_KEY, access)
  wx.setStorageSync(REFRESH_KEY, refresh)
}

function clearTokens() {
  wx.removeStorageSync(TOKEN_KEY)
  wx.removeStorageSync(REFRESH_KEY)
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
    const token = getToken()
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

/** 用 refresh token 换取新的 access token（旧员工 JWT，保留） */
function refreshAccessToken() {
  const refresh = getRefreshToken()
  if (!refresh) return Promise.reject(new Error('未登录'))
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${BASE_URL}/auth/refresh/`,
      method: 'POST',
      data: { refresh },
      header: { 'Content-Type': 'application/json' },
      success(res) {
        if (res.statusCode === 200 && res.data && res.data.access) {
          setTokens(res.data.access, refresh)
          resolve(true)
        } else {
          reject(new Error(extractError(res.data)))
        }
      },
      fail() {
        reject(new Error('网络连接失败'))
      },
    })
  })
}

/**
 * 统一请求入口
 * @param {string} url 接口路径，如 '/public/cases/'
 * @param {object} options { method, data, retried }
 */
function request(url, options = {}) {
  const { method = 'GET', data = {}, retried = false } = options
  return rawRequest(url, method, data).catch((err) => {
    // 客户 token：失效即清除登录态，由页面展示“请先登录”（不跳登录页、不刷新）
    if (err.statusCode === 401 && getCustomerToken() && !retried) {
      clearCustomerToken()
      getApp().globalData.userInfo = null
    }
    // 旧员工 JWT：保留 401 自动刷新逻辑
    if (err.statusCode === 401 && getRefreshToken() && !retried) {
      return refreshAccessToken().then(
        () => request(url, { method, data, retried: true }),
        () => {
          clearTokens()
          throw new Error('登录已过期，请重新登录')
        }
      )
    }
    throw err
  })
}

module.exports = {
  request,
  getToken,
  getRefreshToken,
  getCustomerToken,
  setCustomerToken,
  clearCustomerToken,
  setTokens,
  clearTokens,
  extractError,
}

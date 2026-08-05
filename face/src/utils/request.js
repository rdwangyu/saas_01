/**
 * 网络请求封装
 * - 自动携带 JWT access token
 * - 401 时自动用 refresh token 刷新并重试一次
 * - 刷新失败则清除登录态并跳转登录页
 */
const { BASE_URL } = require('../config')

const TOKEN_KEY = 'access_token'
const REFRESH_KEY = 'refresh_token'

function getToken() {
  return wx.getStorageSync(TOKEN_KEY) || ''
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

/** 用 refresh token 换取新的 access token */
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

/** 跳转登录页并清除登录态 */
function toLogin() {
  clearTokens()
  wx.reLaunch({ url: '/pages/login/login' })
}

/**
 * 统一请求入口
 * @param {string} url 接口路径，如 '/cases/'
 * @param {object} options { method, data, retried }
 */
function request(url, options = {}) {
  const { method = 'GET', data = {}, retried = false } = options
  return rawRequest(url, method, data).catch((err) => {
    if (err.statusCode === 401 && getRefreshToken() && !retried) {
      return refreshAccessToken().then(
        () => request(url, { method, data, retried: true }),
        () => {
          // 仅刷新失败时清除登录态并跳转登录页
          toLogin()
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
  setTokens,
  clearTokens,
  extractError,
}

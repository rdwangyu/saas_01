/**
 * 网络请求封装（无鉴权）
 * - 公开接口（公司/案例）与订单绑定接口均免登录，不携带任何 token
 */
const { BASE_URL } = require('../config')

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

/**
 * 统一请求入口
 * @param {string} url 接口路径，如 '/public/cases/' 或 '/bind-project/'
 * @param {object} options { method, data }
 */
function request(url, options = {}) {
  const { method = 'GET', data = {} } = options
  return new Promise((resolve, reject) => {
    wx.request({
      url: BASE_URL + url,
      method,
      data,
      header: { 'Content-Type': 'application/json' },
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

module.exports = { request, extractError }

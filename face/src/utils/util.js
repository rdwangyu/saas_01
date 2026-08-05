/**
 * 通用工具函数
 */
const { MEDIA_BASE } = require('../config')

function pad(n) {
  return n < 10 ? `0${n}` : `${n}`
}

/** '2026-08-04T16:59:00+08:00' -> '2026-08-04' */
function formatDate(str) {
  if (!str) return ''
  const d = new Date(str)
  if (isNaN(d.getTime())) return str
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/** '2026-08-04T16:59:00+08:00' -> '2026-08-04 16:59' */
function formatDateTime(str) {
  if (!str) return ''
  const d = new Date(str)
  if (isNaN(d.getTime())) return str
  return `${formatDate(str)} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/**
 * 将后端返回的媒体地址规范化为完整 URL
 * 相对路径（如 company_logo/xx.png）拼接 OSS 域名，完整 URL 原样返回
 */
function absUrl(url) {
  if (!url) return ''
  if (/^https?:\/\//i.test(url)) return url
  return MEDIA_BASE + url
}

/** 预算：'38.50' -> '38.5万' */
function formatBudget(v) {
  if (v === null || v === undefined || v === '') return ''
  const n = parseFloat(v)
  if (isNaN(n)) return ''
  return `${n}万`
}

/** 取字符串首字符（用于头像占位） */
function initial(name) {
  if (!name) return '?'
  return name.trim().charAt(0).toUpperCase()
}

module.exports = {
  formatDate,
  formatDateTime,
  absUrl,
  formatBudget,
  initial,
}

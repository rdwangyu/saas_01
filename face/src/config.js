/**
 * 全局配置
 *
 * 开发环境：
 *  - 后端在本机运行时使用 http://127.0.0.1:8000
 *  - 微信开发者工具需勾选「不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书」
 *  - 真机调试时请把 BASE_URL 改为电脑的局域网 IP，如 http://192.168.1.100:8000
 *
 * 生产环境：
 *  - 改为正式 https 域名（如 https://api.example.com），并在微信公众平台
 *    小程序后台配置 request 合法域名
 */
module.exports = {
  // Django 后端 API 根地址（对应 saas/urls.py 中的 /api/）
  BASE_URL: 'http://192.168.10.107:8000/api',

  // 媒体文件兜底域名（阿里云 OSS，settings.py 中 ALIYUN_OSS_BUCKET_DOMAIN）
  // 后端返回的图片/视频地址若为相对路径，会自动拼接该域名
  MEDIA_BASE: 'https://byqg-image.oss-cn-beijing.aliyuncs.com/',
}

# 云序效果图 · 微信小程序

基于 `../app`（Django + DRF）后台的前台小程序。客户用「手机号 + 验证码」登录，进入公司后可查看公司简介、案例与本人项目进度。

## 功能与接口对照

| 功能 | 页面 | 后端接口 | 鉴权 |
| --- | --- | --- | --- |
| 进入公司（输入公司 ID） | `pages/index/` | `GET /api/public/companies/{id}/` | 公开 |
| 公司简介 | `pages/company/` | `GET /api/public/companies/{id}/` | 公开 |
| 案例列表 | `pages/cases/` | `GET /api/public/cases/?company={id}` | 公开 |
| 案例详情 | `pages/case-detail/` | `GET /api/public/cases/{id}/` | 公开 |
| 发送验证码 | `pages/login/` | `POST /api/customer/send-code/` | 公开 |
| 客户登录 | `pages/login/` | `POST /api/customer/login/` | 公开 |
| 我的信息 | `pages/users/` | `GET /api/customer/me/` | 客户 token |
| 我的项目列表 | `pages/projects/` | `GET /api/customer/projects/?company={id}` | 客户 token |
| 项目进度详情 | `pages/project-detail/` | `GET /api/customer/projects/{id}/` | 客户 token |

- 案例/项目列表为分页返回（`{count, next, previous, results}`），列表页支持上拉加载更多与下拉刷新
- 公开接口（公司/案例）免登录；客户接口需登录后在请求头携带 `Authorization: Bearer <customer_token>`
- 登录手机号必须是后台 `Customer` 表中已登记的手机号，未登记会返回「该手机号未登记」

## 目录结构

```
src/
├── app.js                  # 全局入口：进入公司 ID 缓存、客户信息、登录后跳转
├── app.json                # 页面路由 + tabBar 配置
├── app.wxss                # 全局样式（卡片/按钮/渐变页/登录引导等）
├── config.js               # BASE_URL 等配置（改这里切换环境）
├── utils/
│   ├── request.js          # 请求封装：自动携带 customer_token，401 时清除登录态
│   └── util.js             # 日期/金额/媒体地址格式化
├── components/empty/       # 空状态组件
├── pages/                  # 页面
└── images/tabbar/          # tabBar 图标
```

## 运行步骤

1. 启动 Django 后端：`python manage.py runserver 0.0.0.0:8000`
2. 打开微信开发者工具，导入本目录（`face/src`），AppID 已在 `project.config.json` 配置（wx978f49a670b0aa59）
3. 开发者工具 → 详情 → 本地设置 → 勾选「不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书」
4. 在后台 `Customer` 表中登记测试客户的手机号，即可在小程序登录

## 环境切换

- **本机调试**：`config.js` 中 `BASE_URL` 保持 `http://127.0.0.1:8000/api`
- **真机调试**：把 `BASE_URL` 改为电脑局域网 IP，如 `http://192.168.1.100:8000/api`
- **生产环境**：改为 `https://正式域名/api`，并在微信公众平台配置 request 合法域名

## 说明

- 图片/视频地址为阿里云 OSS 完整 URL；若后端返回相对路径，`utils/util.js` 的 `absUrl()` 会自动拼接 `MEDIA_BASE`
- 后端 `SendCodeView` 在测试模式（`SMS_TEST_MODE=True`）下不真正发短信，验证码打印到日志并随响应返回，便于联调

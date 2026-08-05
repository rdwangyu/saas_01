# 云序效果图 · 微信小程序

基于 `../app`（Django + DRF + JWT）后台生成的微信小程序，当前包含四个模块：

| 模块 | Tab | 页面 | 后端接口 |
| --- | --- | --- | --- |
| 公司简介 | 1 | `pages/company/` | `GET /api/companies/` |
| 案例 | 2 | `pages/cases/`、`pages/case-detail/` | `GET /api/cases/`、`GET /api/cases/{id}/` |
| 项目进度 | 3 | `pages/projects/`、`pages/project-detail/` | `GET /api/projects/`、`GET /api/projects/{id}/` |
| 用户管理 | 4 | `pages/users/` | `GET/POST /api/users/`、`PATCH/DELETE /api/users/{id}/`、`GET /api/me/` |

另有 `pages/login/` 登录页（`POST /api/auth/login/`），所有接口均需 JWT 鉴权。

## 目录结构

```
src/
├── app.js                  # 全局入口：已登录自动进入首页
├── app.json                # 页面路由 + tabBar 配置
├── app.wxss                # 全局样式（卡片/按钮/弹窗等）
├── config.js               # BASE_URL 等配置（改这里切换环境）
├── utils/
│   ├── request.js          # 请求封装：自动携带 token、401 自动刷新并重试
│   └── util.js             # 日期/金额/媒体地址格式化
├── components/empty/       # 空状态组件
├── pages/                  # 页面
└── images/tabbar/          # tabBar 图标（scripts/gen_tabbar_icons.ps1 可重新生成）
```

## 运行步骤

1. 启动 Django 后端：`python manage.py runserver 0.0.0.0:8000`
2. 打开微信开发者工具，导入本目录（`face/src`），AppID 已在 `project.config.json` 配置（wx978f49a670b0aa59）
3. 开发者工具 → 详情 → 本地设置 → 勾选「不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书」
4. 登录后台创建的公司管理员账号即可使用

## 环境切换

- **本机调试**：`config.js` 中 `BASE_URL` 保持 `http://127.0.0.1:8000/api`
- **真机调试**：把 `BASE_URL` 改为电脑局域网 IP，如 `http://192.168.1.100:8000/api`
- **生产环境**：改为 `https://正式域名/api`，并在微信公众平台配置 request 合法域名

## 说明

- 后端列表接口为分页返回（`{count, next, previous, results}`），列表页支持上拉加载更多与下拉刷新
- 图片/视频地址为阿里云 OSS 完整 URL；若后端返回相对路径，`utils/util.js` 的 `absUrl()` 会自动拼接 `MEDIA_BASE`
- 用户管理支持：新增用户、删除用户（不能删除自己）、修改当前账号密码、退出登录
- 后端 `app/serializers.py` 的 `UserSerializer` 已补充 `password` 字段与哈希逻辑（`update()` 中 `set_password`），使「修改密码」接口可用；如已部署旧版本请同步更新

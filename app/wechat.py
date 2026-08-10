"""微信小程序服务：获取 access_token、生成小程序码（客户扫码直接进入对应公司）。"""

import requests
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import WechatAccessToken

TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
CODE_URL = "https://api.weixin.qq.com/wxa/getwxacodeunlimit"


class WechatError(Exception):
    """微信接口返回错误。"""


def get_access_token(force=False):
    """获取（并缓存）小程序 access_token；失效或 force 时重新获取。"""
    cached = WechatAccessToken.objects.first()
    if not force and cached and cached.expires_at > timezone.now():
        return cached.token

    resp = requests.get(
        TOKEN_URL,
        params={
            "grant_type": "client_credential",
            "appid": settings.WECHAT_MINI_PROGRAM_APPID,
            "secret": settings.WECHAT_MINI_PROGRAM_SECRET,
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("errcode"):
        raise WechatError(f"获取 access_token 失败：{data.get('errmsg', '未知错误')}")

    token = data["access_token"]
    expires_in = int(data.get("expires_in", 7200))
    # 提前 10 分钟刷新
    expires_at = timezone.now() + timedelta(seconds=max(expires_in - 600, 60))
    if cached:
        cached.token = token
        cached.expires_at = expires_at
        cached.save(update_fields=["token", "expires_at"])
    else:
        WechatAccessToken.objects.create(token=token, expires_at=expires_at)
    return token


def generate_company_code(company_id, width=430):
    """生成公司小程序码，返回 PNG 二进制；scene 携带 company_{id}。"""
    payload = {
        "scene": f"company_{company_id}",
        "page": "pages/company/company",
        "width": width,
        "check_path": False,
    }
    token = get_access_token()
    resp = requests.post(CODE_URL, params={"access_token": token}, json=payload, timeout=15)
    resp.raise_for_status()

    # 成功返回图片二进制；失败返回 JSON 错误
    if "json" in resp.headers.get("content-type", ""):
        data = resp.json()
        errcode = data.get("errcode")
        if errcode in (40001, 42001):  # access_token 无效/过期 → 强制刷新重试一次
            token = get_access_token(force=True)
            resp = requests.post(CODE_URL, params={"access_token": token}, json=payload, timeout=15)
            resp.raise_for_status()
            if "json" in resp.headers.get("content-type", ""):
                data = resp.json()
                raise WechatError(f"生成小程序码失败：{data.get('errmsg', '未知错误')}")
            return resp.content
        raise WechatError(f"生成小程序码失败：{data.get('errmsg', '未知错误')}")
    return resp.content

import logging

from io import BytesIO
from urllib.parse import quote

from django.conf import settings
from django.core.files.base import File
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible
from oss2 import Auth, Bucket
from oss2.exceptions import NotFound

logger = logging.getLogger(__name__)


class OSSNotConfigured(Exception):
    """OSS AccessKey 未配置，无法签名直传。"""


@deconstructible
class OSSStorage(Storage):
    def __init__(self):
        self.access_key_id = settings.ALIYUN_OSS_ACCESS_KEY_ID
        self.access_key_secret = settings.ALIYUN_OSS_ACCESS_KEY_SECRET
        self.bucket_name = settings.ALIYUN_OSS_BUCKET_NAME
        self.endpoint = settings.ALIYUN_OSS_ENDPOINT
        self.bucket_domain = settings.ALIYUN_OSS_BUCKET_DOMAIN

        auth = Auth(self.access_key_id, self.access_key_secret)
        self.bucket = Bucket(auth, self.endpoint, self.bucket_name)

    def delete(self, name):
        key = name.replace("\\", "/")
        try:
            self.bucket.delete_object(key)
        except NotFound:
            pass

def sign_upload_url(key, expires=600):
    if not settings.ALIYUN_OSS_ACCESS_KEY_ID:
        raise OSSNotConfigured("OSS 未配置，无法上传")
    auth = Auth(settings.ALIYUN_OSS_ACCESS_KEY_ID, settings.ALIYUN_OSS_ACCESS_KEY_SECRET)
    # 用 https endpoint 生成签名，避免 https 页面 PUT http 地址被混合内容拦截
    bucket = Bucket(
        auth, f"https://{settings.ALIYUN_OSS_ENDPOINT}", settings.ALIYUN_OSS_BUCKET_NAME
    )
    upload_url = bucket.sign_url("PUT", key, expires)
    file_url = f"https://{settings.ALIYUN_OSS_BUCKET_DOMAIN}/{quote(key, safe='/')}"
    return upload_url, file_url

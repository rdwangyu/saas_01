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

    def _key(self, name):
        return name.replace("\\", "/")

    def _save(self, name, content):
        logger.info("_save called: name=%s", name)
        key = self._key(name)
        content.seek(0)
        data = content.read()
        logger.info("_save: uploading %d bytes to %s", len(data), key)
        result = self.bucket.put_object(key, data)
        if result.status != 200:
            raise IOError(f"OSS upload failed (status {result.status})")
        logger.info("_save: upload OK, request_id=%s", result.request_id)
        return name

    def _open(self, name, mode="rb"):
        key = self._key(name)
        result = self.bucket.get_object(key)
        data = result.read()
        return File(BytesIO(data), name)

    def delete(self, name):
        key = self._key(name)
        try:
            self.bucket.delete_object(key)
        except NotFound:
            pass

    def exists(self, name):
        key = self._key(name)
        try:
            self.bucket.get_object_meta(key)
            return True
        except NotFound:
            return False

    def url(self, name):
        key = quote(self._key(name), safe="/")
        return f"https://{self.bucket_domain}/{key}"

    def size(self, name):
        key = self._key(name)
        result = self.bucket.get_object_meta(key)
        return int(result.headers.get("content-length", 0))

    def path(self, name):
        raise NotImplementedError("OSS storage has no local path")

    def get_accessed_time(self, name):
        key = self._key(name)
        result = self.bucket.get_object_meta(key)
        return result.headers.get("last-modified")

    def get_modified_time(self, name):
        key = self._key(name)
        result = self.bucket.get_object_meta(key)
        return result.headers.get("last-modified")


def sign_upload_url(key, expires=600):
    """生成 OSS PUT 签名 URL（前端直传用）。返回 (upload_url, file_url)。

    upload_url 供前端直接 PUT 文件（前端 PUT 时必须不带 Content-Type 头，
    否则与签名不符会 403）；file_url 是上传后的公开访问地址。
    """
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

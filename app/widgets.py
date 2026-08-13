from django import forms


class OssUrlInput(forms.TextInput):
    """OSS 直传输入框：选文件 → 后端签名 → 直接 PUT 到 OSS → 只存 URL，带预览。

    accept: 文件类型（image/* 或 video/*）；dir: OSS 目录（company_case / company_logo / company_project_progress）。
    """

    template_name = "widgets/oss_url_input.html"

    def __init__(self, attrs=None, accept="image/*", dir=""):
        self.accept = accept
        self.upload_dir = dir
        super().__init__(attrs)

    def get_context(self, name, value, attrs):
        ctx = super().get_context(name, value, attrs)
        ctx["widget"]["accept"] = self.accept
        ctx["widget"]["upload_dir"] = self.upload_dir
        ctx["widget"]["is_video"] = self.accept.startswith("video")
        return ctx

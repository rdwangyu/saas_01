from django import forms


class SimpleFileInput(forms.ClearableFileInput):
    """简约文件上传：只显示上传按钮 + 已上传/无文件状态。无清除复选框。"""

    template_name = "widgets/simple_file.html"
    use_fieldset = False

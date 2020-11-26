from django.core.files.storage import Storage
from fdfs_client.client import Fdfs_client


class FDFStorage(Storage):
    """Fastdfs文件存储类"""

    def _open(self, name, model="db"):
        """打开文件时使用"""
        pass

    def _save(self, name, content):
        """保存文件时使用"""
        # name: 你选择的上传文件的名字
        # content: 包含你上传文件内容的File对象

        # 创建一个Fdfs_client类的对象
        client = Fdfs_client('./utils/fdfs/client.conf')

        # 上传文件到fastdfs系统中
        res = client.upload_by_buffer(content.read())

        if res.get('Status') != 'Upload successed.':
            # 上传失败
            raise Exception("上传文件到fastdfs失败")

        filename = res.get('Remote file_id')
        return filename

    def exists(self, name):
        return False
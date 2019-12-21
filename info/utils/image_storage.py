# 封装图片上传的类
from qiniu import Auth, put_data

access_key = "kL9dN3l23WpQeXKhJzU9jbIK7yyiL93ElSgBMGTu"
secret_key = "N-3N-qoe1H95ZA6VD-GN657NzXBArBbIMs2aX8f1"
bucket_name = "chengaddone"


def storage(data):
    try:
        q = Auth(access_key, secret_key)
        token = q.upload_token(bucket_name)
        ret, info = put_data(token, None, data)
    except Exception as e:
        raise e
    if info.status_code != 200:
        raise Exception("图片上传失败")
    return ret["key"]


if __name__ == '__main__':
    file = input("请输入文件路径")
    with open(file, 'rb') as f:
        storage(f.read())


import rsa
import base64

# 公钥 PEM 格式字符串
pub_key_pem = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCkA9WqirWQII3D8/M9UG8X8ybQ
Ou+cPSNTgR9b4HenJ7A5zSfkXZnetb5q6MmKTJLGCl9MSsHveQPHmLGDG+xw2MlB
w3Yefd/jJ1Cg8pP69wlHRX+wiyh5p8KY55ehFNsQLm3kDGXgVJdtrZn/MiBOlCtE
fe9YvvT0lqy2BtBpaQIDAQAB
-----END PUBLIC KEY-----"""

# 加载公钥
pub_key = rsa.PublicKey.load_pkcs1_openssl_pem(pub_key_pem.encode())

# 获取用户输入的明文密码
password = input().strip()
if not password:
    exit(1)

# 用公钥加密
cipher = rsa.encrypt(password.encode(), pub_key)

# 转 base64，和前端 jsencrypt 的输出一样
cipher_base64 = base64.b64encode(cipher).decode()

print(cipher_base64)

import base64
import requests
from Cryptodome.Cipher import AES
from Cryptodome.Util.number import long_to_bytes
from app.lingxing_agent.core.config import ACCOUNT, PWD


class LingXingAuth:
    BASE_URL = "https://gw.lingxingerp.com"
    HEADERS = {
        "authority": "gw.lingxingerp.com",
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
        "origin": "https://erp.lingxing.com",
        "referer": "https://erp.lingxing.com/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
        "x-ak-company-id": "901217529031491584",
        "x-ak-request-source": "erp",
    }

    @staticmethod
    def _utf8_parse(s):
        b = s.encode("utf-8")
        length = (len(b) + 3) // 4
        words = [0] * length
        for i in range(len(b)):
            word_index = i // 4
            byte_index = i % 4
            words[word_index] |= b[i] << (24 - byte_index * 8)
        return words

    @staticmethod
    def _encrypt_aes(plaintext, key):
        cipher = AES.new(key.encode(), AES.MODE_ECB)
        # PKCS7 padding logic
        pad_len = AES.block_size - len(plaintext) % AES.block_size
        padded_plaintext = plaintext + pad_len * chr(pad_len)
        ciphertext = cipher.encrypt(padded_plaintext.encode())
        return base64.b64encode(ciphertext).decode()

    def get_login_secret_key(self):
        url = f"{self.BASE_URL}/newadmin/api/passport/getLoginSecretKey"
        response = requests.post(url, headers=self.HEADERS, json={})
        if response.status_code == 200:
            return response.json()["data"]
        raise Exception(f"Failed to get secret key: {response.text}")

    def login(self):
        secret_data = self.get_login_secret_key()
        secret_key = secret_data["secretKey"]
        secret_id = secret_data["secretId"]

        encrypted_pwd = self._encrypt_aes(PWD, secret_key)

        login_payload = {
            "account": ACCOUNT,
            "pwd": encrypted_pwd,
            "verify_code": "",
            "uuid": "254cd273-7e74-4f22-ba3e-ae199adbff19",
            "auto_login": 1,
            "secretId": secret_id,
        }

        url = f"{self.BASE_URL}/newadmin/api/passport/login"
        response = requests.post(url, headers=self.HEADERS, json=login_payload)

        if response.status_code == 200:
            data = response.json()
            if "token" in data:
                return data["token"]
            # Sometimes token is directly in response or inside data, based on original code it returns response directly
            # Original code: return response['token'] (after extracting from json)
            # Let's check original code: res['token']
            return data.get("token")

        raise Exception(f"Login failed: {response.text}")


def get_token():
    auth = LingXingAuth()
    return auth.login()

import http.server
import socketserver
from urllib.parse import urlparse, parse_qs
import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 设置服务器IP和端口
HOST = '0.0.0.0'  # 监听所有IP地址
PORT = 6002        # 端口号

# 从环境变量中获取 SECRET_KEY
DIRECTORY = "/mnt/audio/media-separator"

# 固定的secret密钥
SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret')

class StaticFileServe(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # 解析URL路径并检查secret参数
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)
        secret = query_params.get('secert', [None])[0]  # 获取请求中的secert参数

        if secret != SECRET_KEY:
            # 如果没有提供或提供错误的secert，拒绝访问
            self.send_response(403)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"Forbidden: Invalid or missing secret.")
            return

        # 如果校验通过，继续处理请求
        super().do_GET()

    def translate_path(self, path):
        # 调用父类的translate_path方法返回文件路径
        path = super().translate_path(path)
        return path.replace(self.directory, DIRECTORY)

# 设置服务器
with socketserver.TCPServer((HOST, PORT), StaticFileServe) as httpd:
    print(f"Serving on {HOST}:{PORT}")
    httpd.serve_forever()

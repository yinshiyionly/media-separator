import http.server
import socketserver
import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# 从环境变量中获取配置
HOST = os.getenv('HOST', '0.0.0.0')  # 默认监听所有IP地址
PORT = int(os.getenv('PORT', '6002'))  # 默认端口号
DIRECTORY = os.getenv('DIRECTORY', '/opt')  # 默认静态文件目录

class StaticFileServe(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        # 修改默认的路径来返回自定义的静态文件目录
        path = super().translate_path(path)
        return path.replace(self.directory, DIRECTORY)

# 设置服务器
with socketserver.TCPServer((HOST, PORT), StaticFileServe) as httpd:
    print(f"Serving on {HOST}:{PORT} from directory {DIRECTORY}")
    httpd.serve_forever()
import http.server
import socketserver

# 设置服务器IP和端口
HOST = '0.0.0.0'  # 监听所有IP地址
PORT = 6002        # 端口号

# 设置静态文件目录
DIRECTORY = "/mnt/audio/media-separator"

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        # 修改默认的路径来返回自定义的静态文件目录
        path = super().translate_path(path)
        return path.replace(self.directory, DIRECTORY)

# 设置服务器
with socketserver.TCPServer((HOST, PORT), MyHandler) as httpd:
    print(f"Serving on {HOST}:{PORT}")
    httpd.serve_forever()

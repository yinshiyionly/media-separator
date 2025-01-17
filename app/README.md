1. 统一端口号 8000 8001
2. sv 缺少 aiohttp
3. 代码文件映射



# 人声分离
curl --location 'http://127.0.0.1:8000/separate-audio/' \
--form 'url="https://ad-page.cdn.bcebos.com/ldh-by.mp3"' \
--form 'model="UVR-MDX-NET-Inst_HQ_3.onnx"'




# 音频文件提取文字
curl --location 'http://127.0.0.1:8001/extract_text' \
--form 'url="https://ad-page.cdn.bcebos.com/test-UVR-vocal.wav"'








ssh root@8.130.117.208


Duan123456
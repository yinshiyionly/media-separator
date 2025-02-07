## Media Separator
> 音视频文案提取

### 步骤
1. 使用 audio-separator 将音视频进行人声分离,分离出两个音频文件 vocal.wav 和 other.wav
2. 使用 sense-voice 将







### 服务规范
1. audio-separator 容器简称 as, 区分 CPU 和 GPU 版本, 暴露端口 6000
2. sense-voice 容器简称 sv,暴露端口 6001
3. 静态文件服务 6002 
4. 统一端口号 6000 6001
5. sv 缺少 aiohttp 
6. 代码文件映射



# 人声分离
curl --location 'http://127.0.0.1:6005/separate-audio/' \
--form 'url="https://ad-page.bj.bcebos.com/test-audio-remover.mp4"' \
--form 'model="UVR-MDX-NET-Inst_HQ_3.onnx"'




# 音频文件提取文字
curl --location 'http://127.0.0.1:8001/extract_text' \
--form 'url="https://ad-page.bj.bcebos.com/test-UVR-vocal.wav"'

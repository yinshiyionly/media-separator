import os
import uuid
import logging
import aiohttp
from pathlib import Path
from config import settings
from audio_separator.separator import Separator

logger = logging.getLogger(__name__)

class AudioSeparatorProcessor:
    def __init__(self):
        self.separator = Separator(
            log_level=logging.INFO,
            output_single_stem="Vocals",
            model_file_dir=settings.MODEL_DIR,
            output_dir=settings.OUTPUT_DIR
        )

    async def handle_input(self, file, url, request_id):
        """统一处理文件或 URL 逻辑"""
        if file:
            return await self.save_upload_file(file, request_id)
        else:
            return await self.download_file(url, request_id)

    async def download_file(self, url: str, request_id: str) -> str:
        """从URL下载文件"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise HTTPException(status_code=response.status, detail="Failed to download file")

                filename = f"{uuid.uuid4().hex}.mp3"
                file_path = os.path.join(settings.TEMP_DIR, filename)

                with open(file_path, 'wb') as f:
                    f.write(await response.read())

                return file_path

    async def save_upload_file(self, file, request_id) -> str:
        """保存上传文件"""
        file_path = os.path.join(settings.TEMP_DIR, f"{uuid.uuid4().hex}_{file.filename}")
        with open(file_path, "wb") as f:
            f.write(await file.read())
        return file_path

    def process_audio(self, input_file: str, model: str, request_id: str):
        """处理音频"""
        self.separator.load_model(model_filename=model)
        return self.separator.separate(input_file)

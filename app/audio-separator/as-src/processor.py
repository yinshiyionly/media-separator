import os
import uuid
import logging
import aiohttp
from fastapi import HTTPException

from config import settings
from audio_separator.separator import Separator

logger = logging.getLogger(__name__)


class AudioSeparatorProcessor:
    def __init__(self):
        try:
            self.separator = Separator(
                log_level=logging.INFO,
                output_single_stem="Vocals",
                model_file_dir=settings.MODEL_DIR,
                output_dir=settings.OUTPUT_DIR
            )
        except Exception as e:
            logger.exception("Failed to initialize Separator: %s", e)
            raise RuntimeError("Audio processing initialization failed") from e

    async def handle_input(self, file, url, request_id):
        """统一处理文件或 URL 逻辑"""
        try:
            if file:
                return await self.save_upload_file(file)
            else:
                return await self.download_file(url, request_id)
        except Exception as e:
            logger.exception("Error handling input - request_id: %s, error: %s", request_id, e)
            raise HTTPException(status_code=500, detail="Failed to process input file")

    async def download_file(self, url: str, request_id: str) -> str:
        """从URL下载文件"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise HTTPException(status_code=response.status, detail="Failed to download file")

                    filename = f"{uuid.uuid4().hex}.mp3"
                    file_path = os.path.join(settings.TEMP_DIR, filename)

                    with open(file_path, 'wb') as f:
                        f.write(await response.read())

                    return file_path
        except Exception as e:
            logger.exception("Error downloading file - request_id: %s, url: %s, error: %s", request_id, url, e)
            raise HTTPException(status_code=500, detail="File download failed")

    async def save_upload_file(self, file) -> str:
        """保存上传文件"""
        try:
            file_path = os.path.join(settings.TEMP_DIR, f"{uuid.uuid4().hex}_{file.filename}")
            with open(file_path, "wb") as f:
                f.write(await file.read())
            return file_path
        except Exception as e:
            logger.exception("Error saving uploaded file - file: %s, error: %s", file.filename, e)
            raise HTTPException(status_code=500, detail="Failed to save uploaded file")

    def process_audio(self, input_file: str, model: str, request_id: str):
        """处理音频"""
        try:
            self.separator.load_model(model_filename=model)
            return self.separator.separate(input_file)
        except Exception as e:
            logger.exception("Error processing audio - request_id: %s, file: %s, model: %s, error: %s", request_id,
                             input_file, model, e)
            raise HTTPException(status_code=500, detail="Audio processing failed")

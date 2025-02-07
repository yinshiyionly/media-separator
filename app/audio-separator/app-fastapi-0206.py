from fastapi import FastAPI, UploadFile, Form, HTTPException, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl, Field
from audio_separator.separator import Separator
import traceback
import logging
import aiohttp
import os
from typing import Optional, List
from pathlib import Path
import time
import uuid
from contextlib import asynccontextmanager
import json
from datetime import datetime

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('audio_separator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ApiResponse(BaseModel):
    message: str
    output_files: List[str]
    request_id: str = Field(..., description="Unique identifier for the request")
    processing_time: float = Field(..., description="Processing time in seconds")


class AppConfig:
    def __init__(self):
        self.MODEL_DIR = os.getenv("MODEL_DIR", "/tmp/audio-separator-models")
        self.OUTPUT_DIR = os.getenv("OUTPUT_DIR", "/tmp/audio-separator-outputs")
        self.TEMP_DIR = os.getenv("TEMP_DIR", "/tmp/audio-separator-temp")
        self.MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 100 * 1024 * 1024))  # 100MB
        self.ALLOWED_EXTENSIONS = {'.mp3', '.wav', '.flac', '.m4a', '.ogg'}
        self.BASE_URL = os.getenv("BASE_URL", "http://8.130.117.208:6002")


class AudioSeparatorProcessor:
    def __init__(self, config: AppConfig):
        self.config = config
        self._initialize_directories()
        self._initialize_separator()

    def _initialize_directories(self):
        """初始化所需的目录结构"""
        for directory in [self.config.MODEL_DIR, self.config.OUTPUT_DIR, self.config.TEMP_DIR]:
            Path(directory).mkdir(parents=True, exist_ok=True)
            logger.info(f"Initialized directory: {directory}")

    def _initialize_separator(self):
        """初始化音频分离器"""
        try:
            self.separator = Separator(
                log_level=logging.INFO,
                output_single_stem="Vocals",
                model_file_dir=self.config.MODEL_DIR,
                output_dir=self.config.OUTPUT_DIR
            )
            logger.info("Audio separator initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize separator: {str(e)}")
            raise

    async def download_file(self, url: str, request_id: str) -> str:
        """从URL下载文件到临时目录"""
        logger.info(f"[{request_id}] Starting file download from URL: {url}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"Failed to download file: HTTP {response.status}"
                        )

                    content_length = response.headers.get("content-length")
                    if content_length and int(content_length) > self.config.MAX_FILE_SIZE:
                        raise HTTPException(
                            status_code=413,
                            detail="File size exceeds maximum allowed size"
                        )

                    filename = self._generate_temp_filename(
                        response.headers.get("content-disposition"),
                        url
                    )
                    file_path = os.path.join(self.config.TEMP_DIR, filename)

                    with open(file_path, 'wb') as f:
                        total_size = 0
                        while True:
                            chunk = await response.content.read(8192)
                            if not chunk:
                                break
                            total_size += len(chunk)
                            if total_size > self.config.MAX_FILE_SIZE:
                                os.remove(file_path)
                                raise HTTPException(
                                    status_code=413,
                                    detail="File size exceeds maximum allowed size"
                                )
                            f.write(chunk)

                    logger.info(f"[{request_id}] File downloaded successfully: {file_path}")
                    return file_path

        except aiohttp.ClientError as e:
            logger.error(f"[{request_id}] Download failed: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Download failed: {str(e)}")
        except Exception as e:
            logger.error(f"[{request_id}] Unexpected error during download: {str(e)}")
            raise

    def _generate_temp_filename(self, content_disposition: Optional[str], url: str) -> str:
        """生成临时文件名"""
        if content_disposition and "filename=" in content_disposition:
            filename = content_disposition.split("filename=")[1].strip('"')
        else:
            # 从URL中提取文件名，如果没有则生成随机文件名
            url_path = url.split('/')[-1].split('?')[0]
            filename = url_path if url_path else f"download_{uuid.uuid4().hex[:8]}.mp3"

        # 确保文件扩展名合法
        if not any(filename.lower().endswith(ext) for ext in self.config.ALLOWED_EXTENSIONS):
            filename += '.mp3'

        return filename

    async def save_upload_file(self, file: UploadFile, request_id: str) -> str:
        """保存上传的文件到临时目录"""
        logger.info(f"[{request_id}] Saving uploaded file: {file.filename}")

        if not any(file.filename.lower().endswith(ext) for ext in self.config.ALLOWED_EXTENSIONS):
            raise HTTPException(
                status_code=400,
                detail="Unsupported file format"
            )

        file_path = os.path.join(self.config.TEMP_DIR, f"{uuid.uuid4().hex}_{file.filename}")
        try:
            total_size = 0
            with open(file_path, "wb") as f:
                while True:
                    chunk = await file.read(8192)
                    if not chunk:
                        break
                    total_size += len(chunk)
                    if total_size > self.config.MAX_FILE_SIZE:
                        os.remove(file_path)
                        raise HTTPException(
                            status_code=413,
                            detail="File size exceeds maximum allowed size"
                        )
                    f.write(chunk)

            logger.info(f"[{request_id}] File saved successfully: {file_path}")
            return file_path
        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            logger.error(f"[{request_id}] Error saving file: {str(e)}")
            raise

    def process_audio(self, input_file: str, model: str, request_id: str) -> List[str]:
        """处理音频文件"""
        logger.info(f"[{request_id}] Starting audio processing with model: {model}")
        try:
            self.separator.load_model(model_filename=model)
            random_str = uuid.uuid4().hex[:10]
            output_names = {
                "Vocals": f"vocals_output_{random_str}"
            }
            output_files = self.separator.separate(input_file, output_names)
            logger.info(f"[{request_id}] Audio processing completed successfully")
            return output_files
        except Exception as e:
            logger.error(f"[{request_id}] Error processing audio: {str(e)}")
            raise

    def cleanup(self, file_path: str, request_id: str):
        """清理临时文件"""
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"[{request_id}] Cleaned up temporary file: {file_path}")
            except Exception as e:
                logger.warning(f"[{request_id}] Failed to clean up file {file_path}: {str(e)}")


# 创建应用实例
config = AppConfig()
app = FastAPI(title="Audio Separator API", version="1.0.0")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建处理器实例
processor = AudioSeparatorProcessor(config)


@app.post("/separate-audio/", response_model=ApiResponse)
async def separate_audio(
        model: str = Form(...),
        file: Optional[UploadFile] = File(None),
        url: Optional[str] = Form(None)
):
    request_id = uuid.uuid4().hex
    start_time = time.time()
    logger.info(f"[{request_id}] New request received - Model: {model}")

    if not file and not url:
        logger.error(f"[{request_id}] Neither file nor URL provided")
        raise HTTPException(
            status_code=400,
            detail="Either file or url must be provided"
        )

    if file and url:
        logger.error(f"[{request_id}] Both file and URL provided")
        raise HTTPException(
            status_code=400,
            detail="Please provide either file or url, not both"
        )

    temp_file_path = None
    try:
        # 处理输入文件
        if file:
            temp_file_path = await processor.save_upload_file(file, request_id)
        else:
            temp_file_path = await processor.download_file(url, request_id)

        # 处理音频
        output_files = processor.process_audio(temp_file_path, model, request_id)

        # 构建输出URL
        output_urls = [
            f"{config.BASE_URL}/audio-separator/data/audio-separator-outputs/{output_file}"
            for output_file in output_files
        ]

        processing_time = time.time() - start_time
        logger.info(f"[{request_id}] Request completed successfully in {processing_time:.2f} seconds")

        return ApiResponse(
            message="Audio separation completed successfully",
            output_files=output_urls,
            request_id=request_id,
            processing_time=processing_time
        )

    except HTTPException as e:
        logger.error(f"[{request_id}] HTTP Exception: {str(e)}")
        raise
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"[{request_id}] Unexpected error: {error_details}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
    finally:
        if temp_file_path:
            processor.cleanup(temp_file_path, request_id)


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Audio Separator API server...")
    print("\nAPI Documentation available at: http://127.0.0.1:6000/docs\n")
    uvicorn.run(app, host="0.0.0.0", port=6000)
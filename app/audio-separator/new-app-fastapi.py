from fastapi import FastAPI, UploadFile, Form, HTTPException, File
from pydantic import BaseModel, HttpUrl
from audio_separator.separator import Separator
import traceback
import logging
import aiohttp
import os
from typing import Optional, Union
import tempfile
from pathlib import Path


class ApiResponse(BaseModel):
    message: str
    output_files: list[str]


class AudioSeparatorProcessor:
    def __init__(
            self,
            model_dir: str = "/tmp/audio-separator-models",
            output_dir: str = "/tmp/audio-separator-outputs",
            temp_dir: str = "/tmp/audio-separator-temp"
    ):
        self.model_dir = model_dir
        self.output_dir = output_dir
        self.temp_dir = temp_dir

        # 确保必要的目录存在
        for directory in [model_dir, output_dir, temp_dir]:
            Path(directory).mkdir(parents=True, exist_ok=True)

        self.separator = Separator(
            log_level=logging.INFO,
            output_single_stem="Vocals",
            model_file_dir=model_dir,
            output_dir=output_dir
        )

    async def download_file(self, url: str) -> str:
        """从URL下载文件到临时目录"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Failed to download file: {response.status}"
                    )

                # 使用原始文件名或生成临时文件名
                content_disposition = response.headers.get("content-disposition")
                if content_disposition and "filename=" in content_disposition:
                    filename = content_disposition.split("filename=")[1].strip('"')
                else:
                    filename = f"download_{os.urandom(8).hex()}.mp3"

                file_path = os.path.join(self.temp_dir, filename)
                with open(file_path, 'wb') as f:
                    while True:
                        chunk = await response.content.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)

                return file_path

    async def save_upload_file(self, file: UploadFile) -> str:
        """保存上传的文件到临时目录"""
        file_path = os.path.join(self.temp_dir, file.filename)
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        return file_path

    def process_audio(self, input_file: str, model: str) -> list[str]:
        """处理音频文件"""
        self.separator.load_model(model_filename=model)
        return self.separator.separate(input_file)

    def cleanup(self, file_path: str):
        """清理临时文件"""
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logging.warning(f"Failed to clean up file {file_path}: {str(e)}")


app = FastAPI()

processor = AudioSeparatorProcessor()


@app.post("/separate-audio/", response_model=ApiResponse)
async def separate_audio(
        model: str = Form(...),
        file: Optional[UploadFile] = File(None),
        url: Optional[str] = Form(None)
):
    # 如果用户既没有上传文件，也没有提供 URL
    if not file and not url:
        raise HTTPException(status_code=400, detail="Either 'file' or 'url' must be provided.")

    if file and url:
        raise HTTPException(
            status_code=400,
            detail="Please provide either file or url, not both"
        )

    temp_file_path = None
    try:
        # 处理输入文件
        if file:
            temp_file_path = await processor.save_upload_file(file)
        else:
            temp_file_path = await processor.download_file(str(url))

        # 处理音频
        output_files = processor.process_audio(temp_file_path, model)

        return {
            "message": "Audio separation completed successfully",
            "output_files": output_files
        }

    except Exception as e:
        error_details = traceback.format_exc()
        logging.error(f"An error occurred: {error_details}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # 清理临时文件
        if temp_file_path:
            processor.cleanup(temp_file_path)


if __name__ == "__main__":
    import uvicorn

    print("\nAPI Documentation available at: http://127.0.0.1:8000/docs\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
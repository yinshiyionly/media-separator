from fastapi import FastAPI, Form, UploadFile, HTTPException
from pydantic import HttpUrl, ValidationError, BaseModel, Field
from typing import List, Union, Optional
import aiohttp
from io import BytesIO
import numpy as np
import librosa
from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess


class ApiResponse(BaseModel):
    message: str = Field(..., description="Status message indicating the success of the operation.")
    results: str = Field(..., description="Remove label output")
    label_result: str = Field(..., description="Default output")


class AudioProcessor:
    def __init__(self, model_dir: str, device: str = "cuda:0"):
        self.model = AutoModel(
            model=model_dir,
            trust_remote_code=True,
            remote_code="/app/code/model.py",
            vad_model="fsmn-vad",
            vad_kwargs={"max_single_segment_time": 30000},
            device=device,
        )

    async def process_url(self, url: str) -> np.ndarray:
        """从URL下载并处理音频"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    },
            ) as response:
                if response.status != 200:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Failed to download audio: {response.status}",
                    )
                audio_bytes = await response.read()
                return self.process_audio_bytes(audio_bytes)

    def process_audio_bytes(self, audio_bytes: bytes) -> np.ndarray:
        """处理音频字节数据"""
        audio_io = BytesIO(audio_bytes)
        waveform, sr = librosa.load(audio_io, sr=16000)  # 统一采样率为16kHz
        return waveform

    def generate_text(self,
                      audio_data: np.ndarray,
                      language: str = "zn",
                      use_itn: bool = True) -> dict:
        """生成文本转写结果"""
        return self.model.generate(
            input=audio_data,
            language=language,
            use_itn=use_itn,
            batch_size_s=60,
            merge_vad=True,
            merge_length_s=15,
        )


app = FastAPI()

# 初始化处理器
processor = AudioProcessor(model_dir="/app/iic/SenseVoiceSmall")


@app.post("/extract_text", response_model=ApiResponse)
async def upload_audio(
        url: Optional[HttpUrl] = Form(None),
        file: Optional[UploadFile] = Form(None),
        language: str = Form("zn")
):
    try:
        # 处理音频输入
        if file:
            audio_bytes = await file.read()
            audio_data = processor.process_audio_bytes(audio_bytes)
        elif url:
            audio_data = await processor.process_url(str(url))
        else:
            raise HTTPException(400, detail="No valid audio source provided.")

        # 生成转写结果
        res = processor.generate_text(
            audio_data=audio_data,
            language=language,
            use_itn=True
        )

        # 处理结果
        text = rich_transcription_postprocess(res[0]["text"])

        return {
            "message": "Audio processed successfully",
            "results": text,
            "label_result": res[0]["text"]
        }

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.errors())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    print("\nAPI Documentation available at: http://127.0.0.1:6001/docs\n")
    uvicorn.run(app, host="0.0.0.0", port=6001)
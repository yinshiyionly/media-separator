from fastapi import APIRouter, Form, UploadFile, File, HTTPException
from models import ApiResponse
from processor import AudioSeparatorProcessor
import uuid
import time
from config import settings

router = APIRouter()
processor = AudioSeparatorProcessor()

@router.post("/separate-audio/", response_model=ApiResponse)
async def separate_audio(
    model: str = Form(...),
    file: UploadFile = File(None),
    url: str = Form(None),
):
    request_id = uuid.uuid4().hex
    start_time = time.time()

    if not file and not url:
        raise HTTPException(status_code=400, detail="Either file or url must be provided")
    if file and url:
        raise HTTPException(status_code=400, detail="Provide either file or url, not both")

    temp_file_path = await processor.handle_input(file, url, request_id)
    output_files = processor.process_audio(temp_file_path, model, request_id)

    processing_time = time.time() - start_time
    return ApiResponse(
        message="Audio separation completed successfully",
        output_files=[f"{settings.BASE_URL}/{file}" for file in output_files],
        request_id=request_id,
        processing_time=processing_time
    )

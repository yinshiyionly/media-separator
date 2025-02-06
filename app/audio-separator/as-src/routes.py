import logging
import uuid
import time
from fastapi import APIRouter, Form, UploadFile, File, HTTPException
from models import ApiResponse
from processor import AudioSeparatorProcessor
from config import settings
from pydantic import ValidationError

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

    try:
        # 记录请求信息
        logger.info(
            f"Request received - request_id: {request_id}, model: {model}, file: {file.filename if file else None}, url: {url}")

        if not file and not url:
            raise ValueError("Either file or url must be provided")
        if file and url:
            raise ValueError("Provide either file or url, not both")

        temp_file_path = await processor.handle_input(file, url, request_id)
        output_files = processor.process_audio(temp_file_path, model, request_id)

        processing_time = time.time() - start_time

        response = ApiResponse(
            message="Audio separation completed successfully",
            output_files=[f"{settings.BASE_URL}/{file}" for file in output_files],
            request_id=request_id,
            processing_time=processing_time
        )
        logger.info(f"Request completed - request_id: {request_id}, response: {response}")
        return response

    except ValidationError as e:
        error_message = "Invalid input data"
        logger.error(f"Request failed - request_id: {request_id}, validation_error: {e}")
    except ValueError as e:
        error_message = str(e)
        logger.error(f"Request failed - request_id: {request_id}, error: {error_message}")
    except HTTPException as e:
        error_message = str(e)
        logger.error(f"Request failed - request_id: {request_id}, error: {error_message}")
    except Exception as e:
        error_message = "Internal server error"
        logger.exception(f"Unexpected error - request_id: {request_id}, error: {e}")

    processing_time = time.time() - start_time
    return ApiResponse(
        message=error_message,
        output_files=[],
        request_id=request_id,
        processing_time=processing_time
    )

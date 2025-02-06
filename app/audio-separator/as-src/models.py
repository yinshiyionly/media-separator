from pydantic import BaseModel, Field
from typing import List

class ApiResponse(BaseModel):
    message: str
    output_files: List[str]
    request_id: str = Field(..., description="Unique request ID")
    processing_time: float = Field(..., description="Processing time in seconds")

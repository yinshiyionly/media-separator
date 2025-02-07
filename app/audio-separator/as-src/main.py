from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from routes import router
from config import settings

# 初始化 fastapi
app = FastAPI(title="Audio Separator API", version="1.0.0")

# cors 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 引用路由
app.include_router(router)

# 启动服务
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)

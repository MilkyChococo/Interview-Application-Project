import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi import status, Request
from src.routers.emotion_router import router as emotion_router
from src.routers.mock_agent_router import router as mock_agent_router
from src.routers.evaluation_router import router as evaluation_router
from src.routers import (
    chatbot_router,
    resume_router,
    db_router
)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    exc_str = f'{exc}'.replace('\n', ' ').replace('   ', ' ')
    print(exc_str)
    content = {'status_code': 422, 'detail': exc_str, 'headers': None}
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=content)

# Include routers
app.include_router(chatbot_router)
app.include_router(resume_router)
app.include_router(db_router)
app.include_router(mock_agent_router)
app.include_router(emotion_router)
app.include_router(evaluation_router)
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=3005,
        workers=1,
        # ssl_keyfile="/etc/letsencrypt/live/api.sdhchatbot.top/privkey.pem",
        # ssl_certfile="/etc/letsencrypt/live/api.sdhchatbot.top/fullchain.pem"
    )

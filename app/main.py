from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.rag_api.routes.routes import router
from app.rag_api.models.response import Response

app = FastAPI(
    title="Enterprise RAG Assistant API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(router)


# Handle HTTP exceptions
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=Response(
            status_code=exc.status_code, message=str(exc.detail), data=None
        ).model_dump(),
    )


# Handle unexpected exceptions
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=Response(
            status_code=500, message="Internal Server Error", data=None
        ).model_dump(),
    )

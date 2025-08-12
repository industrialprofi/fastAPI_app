from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database.database import get_db
from database.models import User
from schemas import LLMRequest, LLMResponse
from services.chat_service import get_chat_service, ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=LLMResponse)
async def chat_with_llm(
    request: LLMRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
        chat_service: ChatService = Depends(get_chat_service)
):
    """Send a message to the LLM and get a response"""
    return await chat_service.process_chat_request(request, current_user, db)


@router.post("/stream")
async def chat_with_llm_stream(
        request: LLMRequest,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        chat_service: ChatService = Depends(get_chat_service)
):
    """Send a message to the LLM and get a streaming response via Server-Sent Events"""
    return StreamingResponse(
        chat_service.process_chat_request_stream(request, current_user, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

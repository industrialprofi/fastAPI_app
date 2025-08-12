from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database.database import get_db
from database.models import User
from exceptions import DailyLimitExceededException, MinuteLimitExceededException, NoActiveSubscriptionException
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
    try:
        return await chat_service.process_chat_request(request, current_user, db)
    except DailyLimitExceededException as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=e.message
        )
    except MinuteLimitExceededException as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=e.message
        )
    except NoActiveSubscriptionException as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=e.message
        )
    except ValueError as e:
        # Handle conversation not found and other value errors
        if "Conversation not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Handle other unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat request: {str(e)}"
        )


@router.post("/stream")
async def chat_with_llm_stream(
        request: LLMRequest,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        chat_service: ChatService = Depends(get_chat_service)
):
    """Send a message to the LLM and get a streaming response via Server-Sent Events"""
    try:
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
    except DailyLimitExceededException as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=e.message
        )
    except MinuteLimitExceededException as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=e.message
        )
    except NoActiveSubscriptionException as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=e.message
        )
    except ValueError as e:
        # Handle conversation not found and other value errors
        if "Conversation not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Handle other unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat stream: {str(e)}"
        )

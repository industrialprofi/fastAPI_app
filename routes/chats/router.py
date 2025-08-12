from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from database.database import get_db
from database.models import User, Conversation, Message
from schemas import LLMRequest, LLMResponse, SenderType
from auth import get_current_user
from services.llm_service import get_llm_service, LLMService
from services.rate_limit import get_rate_limit_service, RateLimitService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=LLMResponse)
async def chat_with_llm(
    request: LLMRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    llm_service: LLMService = Depends(get_llm_service),
    rate_limit_service: RateLimitService = Depends(get_rate_limit_service)
):
    """Send a message to the LLM and get a response"""

    # Check rate limits
    await rate_limit_service.check_rate_limit(db, current_user)

    # Get or create conversation
    if request.conversation_id:
        # Get existing conversation
        result = await db.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(
                and_(
                    Conversation.id == request.conversation_id,
                    Conversation.user_id == current_user.id
                )
            )
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
    else:
        # Create new conversation
        title = request.new_conversation_title or llm_service.generate_conversation_title(request.message)
        conversation = Conversation(
            user_id=current_user.id,
            title=title
        )
        db.add(conversation)
        await db.flush()

    # Add user message to conversation
    user_message = Message(
        conversation_id=conversation.id,
        sender_type=SenderType.user,
        content=request.message
    )
    db.add(user_message)
    await db.flush()

    # Get conversation history for context
    if hasattr(conversation, 'messages'):
        messages = list(conversation.messages) + [user_message]
    else:
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at)
        )
        messages = result.scalars().all()

    # Format messages for LLM
    formatted_messages = llm_service.format_conversation_for_llm(messages)

    try:
        # Get LLM response
        llm_response = await llm_service.generate_response(formatted_messages)

        # Add assistant message to conversation
        assistant_message = Message(
            conversation_id=conversation.id,
            sender_type=SenderType.assistant,
            content=llm_response
        )
        db.add(assistant_message)

        # Log the request for rate limiting
        await rate_limit_service.log_request(db, current_user)

        await db.commit()
        await db.refresh(assistant_message)

        return LLMResponse(
            response=llm_response,
            conversation_id=conversation.id,
            message_id=assistant_message.id
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating response: {str(e)}"
        )

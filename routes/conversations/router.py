from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database.database import get_db
from database.models import User, Conversation
from schemas import ConversationCreate, ConversationUpdate, ConversationResponse
from services.conversations_service import ConversationsService

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", response_model=ConversationResponse)
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new conversation"""
    conversation = Conversation(
        user_id=current_user.id,
        title=conversation_data.title
    )

    db.add(conversation)
    await db.commit()
    await db.refresh(conversation, ["messages"])

    return conversation


@router.get("", response_model=List[ConversationResponse])
async def get_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all conversations for the current user"""
    conversations = await ConversationsService.conversations_get(db, current_user.id)
    return conversations


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific conversation with all messages"""

    conversation = ConversationsService.conversation_get(db, current_user.id)

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    return conversation


@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
        conversation_id: int,
        data_to_update: ConversationUpdate,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Update a conversation's title"""
    conversation = await ConversationsService.conversation_update(db, conversation_id, current_user.id)

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    # Update the title if provided
    if data_to_update.title is not None:
        conversation.title = data_to_update.title

    await db.commit()
    await db.refresh(conversation, ["messages"])

    return conversation


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a conversation"""
    conversation = await ConversationsService.conversation_delete(db, conversation_id, current_user.id)

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    await db.delete(conversation)
    await db.commit()

    return {"message": "Conversation deleted successfully"}

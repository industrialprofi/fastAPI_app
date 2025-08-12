from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from database.models import Conversation


class ConversationsService:
    @staticmethod
    async def conversations_get(db: AsyncSession, user_id: int):
        result = await db.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.created_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def conversation_get(db: AsyncSession, user_id: int):
        result = await db.execute(
            select(Conversation)
            .options(joinedload(Conversation.messages))
            .where(
                and_(
                    Conversation.id == user_id,
                    Conversation.user_id == user_id
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def conversation_update(db: AsyncSession, conversation_id, user_id):
        result = await db.execute(
            select(Conversation)
            .options(joinedload(Conversation.messages))
            .where(
                and_(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user_id
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def conversation_delete(db: AsyncSession, conversation_id, user_id):
        result = await db.execute(
            select(Conversation).where(
                and_(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user_id
                )
            )
        )
        return result.scalar_one_or_none()

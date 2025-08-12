import json
from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import User, Conversation, Message
from schemas import LLMRequest, LLMResponse, SenderType
from services.llm_service import LLMService, get_llm_service
from services.rate_limit import RateLimitService, get_rate_limit_service


class ChatService:
    def __init__(self, llm_service: LLMService, rate_limit_service: RateLimitService):
        self.llm_service = llm_service
        self.rate_limit_service = rate_limit_service
        # TODO Define the system message that will be added to all conversations
        self.system_message = "You are a helpful assistant. Answer questions based on the conversation history and provide accurate information."

    def _add_system_message_to_formatted_messages(self, formatted_messages: list[dict[str, str]]) -> list[
        dict[str, str]]:
        """Add system message to the beginning of formatted messages without saving to database"""
        system_message = {
            "role": "system",
            "content": self.system_message
        }

        # Check if there's already a system message at the beginning
        if formatted_messages and formatted_messages[0].get("role") == "system":
            # Replace the first system message with ours
            formatted_messages[0] = system_message
        else:
            # Add our system message at the beginning
            formatted_messages.insert(0, system_message)

        return formatted_messages

    async def process_chat_request(
            self,
            request: LLMRequest,
            current_user: User,
            db: AsyncSession
    ) -> LLMResponse:
        """Process a chat request and return the complete response"""

        # Check rate limits
        await self.rate_limit_service.check_rate_limit(db, current_user)

        # Get or create conversation
        conversation = await self._get_or_create_conversation(request, current_user, db)

        # Add user message to conversation
        user_message = await self._add_user_message(request.message, conversation, db)

        # Get conversation history for context
        messages = await self._get_conversation_messages(conversation, user_message, db)

        # Format messages for LLM
        formatted_messages = self.llm_service.format_conversation_for_llm(messages)

        # Add system message
        formatted_messages_with_system = self._add_system_message_to_formatted_messages(formatted_messages)

        try:
            # Get LLM response
            llm_response = await self.llm_service.generate_response(formatted_messages_with_system)

            # Add assistant message to conversation
            assistant_message = await self._add_assistant_message(llm_response, conversation, db)

            # Log the request for rate limiting
            await self.rate_limit_service.log_request(db, current_user)

            await db.commit()
            await db.refresh(assistant_message)

            return LLMResponse(
                response=llm_response,
                conversation_id=conversation.id,
                message_id=assistant_message.id
            )

        except Exception as e:
            await db.rollback()
            raise Exception(f"Error generating response: {str(e)}")

    async def process_chat_request_stream(
            self,
            request: LLMRequest,
            current_user: User,
            db: AsyncSession
    ) -> AsyncGenerator[str, None]:
        """Process a chat request and stream the response"""

        # Check rate limits
        await self.rate_limit_service.check_rate_limit(db, current_user)

        # Get or create conversation
        conversation = await self._get_or_create_conversation(request, current_user, db)

        # Add user message to conversation
        user_message = await self._add_user_message(request.message, conversation, db)

        # Get conversation history for context
        messages = await self._get_conversation_messages(conversation, user_message, db)

        # Format messages for LLM
        formatted_messages = self.llm_service.format_conversation_for_llm(messages)

        # Add system message to the beginning (not saved to database)
        formatted_messages_with_system = self._add_system_message_to_formatted_messages(formatted_messages)

        try:
            # Send initial metadata
            yield f"data: {json.dumps({'type': 'metadata', 'conversation_id': conversation.id, 'message_id': user_message.id})}\n\n"

            # Stream LLM response
            full_response = ""
            async for chunk in self.llm_service.generate_response_stream(formatted_messages_with_system):
                full_response += chunk
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

            # Add assistant message to conversation
            assistant_message = await self._add_assistant_message(full_response, conversation, db)

            # Log the request for rate limiting
            await self.rate_limit_service.log_request(db, current_user)

            await db.commit()
            await db.refresh(assistant_message)

            # Send completion metadata
            yield f"data: {json.dumps({'type': 'complete', 'message_id': assistant_message.id})}\n\n"

        except Exception as e:
            await db.rollback()
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    async def _get_or_create_conversation(
            self,
            request: LLMRequest,
            current_user: User,
            db: AsyncSession
    ) -> Conversation:
        """Get existing conversation or create a new one"""
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
                raise ValueError("Conversation not found")
            return conversation
        else:
            # Create new conversation
            title = await self.llm_service.generate_conversation_title(request.message)
            conversation = Conversation(
                user_id=current_user.id,
                title=title
            )
            db.add(conversation)
            await db.flush()
            return conversation

    async def _add_user_message(
            self,
            content: str,
            conversation: Conversation,
            db: AsyncSession
    ) -> Message:
        """Add user message to conversation"""
        user_message = Message(
            conversation_id=conversation.id,
            sender_type=SenderType.user,
            content=content
        )
        db.add(user_message)
        await db.flush()
        return user_message

    async def _add_assistant_message(
            self,
            content: str,
            conversation: Conversation,
            db: AsyncSession
    ) -> Message:
        """Add assistant message to conversation"""
        assistant_message = Message(
            conversation_id=conversation.id,
            sender_type=SenderType.assistant,
            content=content
        )
        db.add(assistant_message)
        return assistant_message

    async def _get_conversation_messages(
            self,
            conversation: Conversation,
            user_message: Message,
            db: AsyncSession
    ) -> list[Message]:
        """Get all messages in the conversation including the new user message"""
        if hasattr(conversation, 'messages'):
            messages = list(conversation.messages) + [user_message]
        else:
            result = await db.execute(
                select(Message)
                .where(Message.conversation_id == conversation.id)
                .order_by(Message.created_at)
            )
            messages = result.scalars().all()
        return messages


def get_chat_service(
        llm_service: LLMService = Depends(get_llm_service),
        rate_limit_service: RateLimitService = Depends(get_rate_limit_service)
) -> ChatService:
    """Dependency for getting chat service"""
    return ChatService(llm_service, rate_limit_service)

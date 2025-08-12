from typing import List, Dict, AsyncGenerator

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

from config import settings
from database.models import Message
from schemas import SenderType


class LLMService:
    def __init__(self, model: str = "gpt-4o-mini"):
        """Initialize LangChain ChatOpenAI instance"""
        self.llm = ChatOpenAI(
            model=model,
            temperature=0.7,
            max_tokens=1000,
            api_key=settings.openai_api_key
        )

    async def generate_response(self, messages: List[Dict[str, str]]) -> str:
        """Generate response using LangChain ChatOpenAI"""
        try:
            # Convert messages to LangChain format
            langchain_messages = self._convert_to_langchain_messages(messages)

            # Generate response
            response = await self.llm.ainvoke(langchain_messages)
            return response.content
        except Exception as e:
            raise Exception(f"LLM API error: {str(e)}")

    async def generate_response_stream(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        """Generate streaming response using LangChain ChatOpenAI"""
        try:
            # Convert messages to LangChain format
            langchain_messages = self._convert_to_langchain_messages(messages)

            # Generate streaming response
            async for chunk in self.llm.astream(langchain_messages):
                if hasattr(chunk, 'content') and chunk.content:
                    yield chunk.content
        except Exception as e:
            raise Exception(f"LLM API error: {str(e)}")

    def _convert_to_langchain_messages(self, messages: List[Dict[str, str]]) -> List:
        """Convert OpenAI format messages to LangChain messages"""
        langchain_messages = []

        for message in messages:
            role = message["role"]
            content = message["content"]

            if role == "user":
                langchain_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                langchain_messages.append(AIMessage(content=content))
            elif role == "system":
                langchain_messages.append(SystemMessage(content=content))

        return langchain_messages

    @staticmethod
    def format_conversation_for_llm(messages: List[Message]) -> List[Dict[str, str]]:
        """Convert database messages to OpenAI format"""
        formatted_messages = []

        for message in messages:
            role = "user" if message.sender_type == SenderType.user else "assistant"
            if message.sender_type == SenderType.system:
                role = "system"

            formatted_messages.append({
                "role": role,
                "content": message.content
            })

        return formatted_messages

    async def generate_conversation_title(self, user_message: str) -> str:
        """Generate a title for the conversation using LLM based on the first user message"""
        try:
            # Create a system prompt for title generation
            title_prompt = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that generates concise, descriptive titles for conversations. Generate a short title (max 6 words) that captures the main topic or intent of the user's message. Do not use quotes or special formatting."
                },
                {
                    "role": "user",
                    "content": f"Generate a title for a conversation that starts with: {user_message}"
                }
            ]

            # Convert to LangChain format
            langchain_messages = self._convert_to_langchain_messages(title_prompt)

            # Generate title using LLM
            response = await self.llm.ainvoke(langchain_messages)
            title = response.content.strip()

            # Fallback to simple generation if LLM fails or returns empty
            if not title:
                raise Exception("Empty title generated")

            # Ensure title is not too long
            if len(title) > 50:
                title = title[:47] + "..."

            return title

        except Exception:
            # Fallback to simple title generation if LLM fails
            words = user_message.split()[:5]
            title = " ".join(words)
            if len(title) > 50:
                title = title[:47] + "..."
            return title or "New Conversation"


# Dependency injection function
def get_llm_service() -> LLMService:
    """Dependency injection function for LLM service"""
    return LLMService()

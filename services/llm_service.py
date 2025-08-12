from typing import List, Dict
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
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

    @staticmethod
    def _convert_to_langchain_messages(messages: List[Dict[str, str]]) -> List:
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

    @staticmethod
    def generate_conversation_title(user_message: str) -> str:
        """Generate a title for the conversation based on the first user message"""
        # Simple title generation - take first few words
        words = user_message.split()[:5]
        title = " ".join(words)
        if len(title) > 50:
            title = title[:47] + "..."
        return title or "New Conversation"


# Dependency injection function
def get_llm_service() -> LLMService:
    """Dependency injection function for LLM service"""
    return LLMService()

from datetime import datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, EmailStr


class SenderType(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class MessageResponse(BaseModel):
    id: int
    sender_type: SenderType
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


# Conversation schemas
class ConversationCreate(BaseModel):
    title: Optional[str] = None


class ConversationUpdate(BaseModel):
    title: Optional[str] = None


class ConversationResponse(BaseModel):
    id: int
    title: Optional[str]
    created_at: datetime
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True


# LLM Request/Response schemas
class LLMRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None


class LLMResponse(BaseModel):
    response: str
    conversation_id: int
    message_id: int


# Subscription schemas
class SubscriptionPlanResponse(BaseModel):
    id: int
    name: str
    requests_per_minute: int
    requests_per_day: int
    price: float

    class Config:
        from_attributes = True


class UserSubscriptionResponse(BaseModel):
    id: int
    plan: SubscriptionPlanResponse
    start_date: datetime
    end_date: Optional[datetime]
    active: bool

    class Config:
        from_attributes = True


# User schemas
class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    username: Optional[str]
    email_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class EmailVerificationRequest(BaseModel):
    email: EmailStr


class EmailVerificationResponse(BaseModel):
    message: str


# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str


# Message schemas
class MessageCreate(BaseModel):
    content: str

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from typing import List

from database.database import get_db
from database.models import User, SubscriptionPlan, UserSubscription
from schemas import SubscriptionPlanResponse, UserSubscriptionResponse
from auth import get_current_user

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("/plans", response_model=List[SubscriptionPlanResponse])
async def get_subscription_plans(db: AsyncSession = Depends(get_db)):
    """Get all available subscription plans"""
    result = await db.execute(select(SubscriptionPlan))
    plans = result.scalars().all()
    return plans


@router.get("/my-subscription", response_model=UserSubscriptionResponse)
async def get_my_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's active subscription"""
    result = await db.execute(
        select(UserSubscription)
        .options(selectinload(UserSubscription.plan))
        .where(
            and_(
                UserSubscription.user_id == current_user.id,
                UserSubscription.active == True
            )
        )
        .order_by(UserSubscription.created_at.desc())
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    return subscription

from datetime import datetime, timedelta, UTC

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, RequestLog, UserSubscription, SubscriptionPlan
from exceptions import DailyLimitExceededException, MinuteLimitExceededException, NoActiveSubscriptionException


class RateLimitService:
    @staticmethod
    async def check_rate_limit(db: AsyncSession, user: User) -> bool:
        """Check if user can make a request based on their subscription plan"""

        if user.is_admin:
            return True

        # Get user's active subscription
        subscription_query = select(UserSubscription, SubscriptionPlan).join(
            SubscriptionPlan, UserSubscription.plan_id == SubscriptionPlan.id
        ).where(
            and_(
                UserSubscription.user_id == user.id,
                UserSubscription.active == True,
                UserSubscription.start_date <= datetime.now(UTC),
                (UserSubscription.end_date.is_(None) | (UserSubscription.end_date > datetime.now(UTC)))
            )
        )

        result = await db.execute(subscription_query)
        subscription_data = result.first()

        if not subscription_data:
            # No active subscription - create default free plan if needed
            await RateLimitService.ensure_free_plan(db, user)
            raise NoActiveSubscriptionException()

        subscription, plan = subscription_data

        # Check daily limit
        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        daily_requests = await db.execute(
            select(func.count(RequestLog.id)).where(
                and_(
                    RequestLog.user_id == user.id,
                    RequestLog.requested_at >= today_start
                )
            )
        )
        daily_count = daily_requests.scalar() or 0

        if daily_count >= plan.requests_per_day:
            raise DailyLimitExceededException(plan.requests_per_day)

        # Check per-minute limit
        minute_ago = datetime.now(UTC) - timedelta(minutes=1)
        minute_requests = await db.execute(
            select(func.count(RequestLog.id)).where(
                and_(
                    RequestLog.user_id == user.id,
                    RequestLog.requested_at >= minute_ago
                )
            )
        )
        minute_count = minute_requests.scalar() or 0

        if minute_count >= plan.requests_per_minute:
            raise MinuteLimitExceededException(plan.requests_per_minute)

        return True

    @staticmethod
    async def log_request(db: AsyncSession, user: User):
        """Log a request for rate limiting purposes"""
        request_log = RequestLog(user_id=user.id)
        db.add(request_log)
        await db.commit()

    @staticmethod
    async def ensure_free_plan(db: AsyncSession, user: User):
        """Ensure user has a free plan subscription"""
        # Check if free plan exists
        free_plan = await db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.name == "Free")
        )
        plan = free_plan.scalar_one_or_none()

        if not plan:
            # Create free plan
            plan = SubscriptionPlan(
                name="Free",
                requests_per_minute=5,
                requests_per_day=100,
                price=0.00
            )
            db.add(plan)
            await db.flush()

        # Create subscription for user
        subscription = UserSubscription(
            user_id=user.id,
            plan_id=plan.id,
            active=True
        )
        db.add(subscription)
        await db.commit()


# Dependency injection function
def get_rate_limit_service() -> RateLimitService:
    """Dependency injection function for rate limit service"""
    return RateLimitService()

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta

from database.database import get_db
from database.models import User
from schemas import (
    UserCreate, UserLogin, UserResponse, Token,
    EmailVerificationRequest, EmailVerificationResponse
)
from auth import (
    get_password_hash, authenticate_user, create_access_token,
    get_current_user, get_user_by_email, oauth, get_or_create_oauth_user
)
from services.rate_limit import get_rate_limit_service, RateLimitService
from services.email_service import get_email_service, EmailService
from config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=EmailVerificationResponse)
async def register(
    user_data: UserCreate, 
    db: AsyncSession = Depends(get_db),
    email_service: EmailService = Depends(get_email_service)
):
    """Register a new user and send confirmation email"""
    # Check if user already exists
    existing_user = await get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Generate email verification token
    verification_token = email_service.generate_confirmation_token(user_data.email)

    # Create new user (unverified)
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        password_hash=hashed_password,
        email_verified=False,
        email_verification_token=verification_token
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Send confirmation email
    try:
        await email_service.send_confirmation_email(
            email=user_data.email,
            username=user_data.username,
            token=verification_token
        )
    except Exception as e:
        # If email fails, still allow registration but log error
        print(f"Failed to send confirmation email: {e}")

    return EmailVerificationResponse(
        message="Registration successful! Please check your email to verify your account."
    )


@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """Authenticate user and return access token"""
    user = await authenticate_user(db, user_credentials.email, user_credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/verify-email")
async def verify_email_with_token(
    token: str,
    db: AsyncSession = Depends(get_db),
    email_service: EmailService = Depends(get_email_service),
    rate_limit_service: RateLimitService = Depends(get_rate_limit_service)
):
    """Verify email address using token from email link"""
    # Verify token and get email
    email = email_service.verify_confirmation_token(token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )

    # Find user by email
    user = await get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user.email_verified:
        return {"message": "Email already verified"}

    # Mark email as verified
    user.email_verified = True
    user.email_verification_token = None
    await db.commit()

    # Create default free subscription
    await rate_limit_service.ensure_free_plan(db, user)

    return {"message": "Email verified successfully! You can now log in."}


@router.post("/resend-verification", response_model=EmailVerificationResponse)
async def resend_verification_email(
    request: EmailVerificationRequest,
    db: AsyncSession = Depends(get_db),
    email_service: EmailService = Depends(get_email_service)
):
    """Resend verification email"""
    user = await get_user_by_email(db, request.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )

    # Generate new verification token
    verification_token = email_service.generate_confirmation_token(request.email)
    user.email_verification_token = verification_token
    await db.commit()

    # Send confirmation email
    try:
        await email_service.send_confirmation_email(
            email=request.email,
            username=user.username or "User",
            token=verification_token
        )
        return EmailVerificationResponse(
            message="Verification email sent! Please check your inbox."
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email"
        )


@router.get("/{provider}")
async def oauth_login(provider: str, request: Request):
    """Initiate OAuth login with provider (google, github)"""
    if provider not in ['google', 'github']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported OAuth provider"
        )

    client = oauth.create_client(provider)
    redirect_uri = f"{settings.app_url}/auth/callback/{provider}"
    return await client.authorize_redirect(request, redirect_uri)


@router.get("/callback/{provider}")
async def oauth_callback(
    provider: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle OAuth callback"""
    if provider not in ['google', 'github']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported OAuth provider"
        )

    try:
        client = oauth.create_client(provider)
        token = await client.authorize_access_token(request)

        # Get user info from provider
        if provider == 'google':
            user_info = token.get('userinfo')
            if not user_info:
                user_info = await client.parse_id_token(request, token)
        elif provider == 'github':
            resp = await client.get('user', token=token)
            user_info = resp.json()
            # Get email separately for GitHub
            email_resp = await client.get('user/emails', token=token)
            emails = email_resp.json()
            primary_email = next((email['email'] for email in emails if email['primary']), None)
            user_info['email'] = primary_email
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported OAuth provider"
            )

        # Add token info to user_info
        user_info['access_token'] = token.get('access_token')
        user_info['refresh_token'] = token.get('refresh_token')

        # Get or create user
        user = await get_or_create_oauth_user(db, provider, user_info)

        # Create access token
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )

        # Redirect to frontend with token (in a real app, you'd handle this more securely)
        return RedirectResponse(
            url=f"{settings.app_url}/?token={access_token}&token_type=bearer"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth authentication failed: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user

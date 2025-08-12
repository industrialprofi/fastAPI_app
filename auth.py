from datetime import datetime, timedelta
from typing import Optional
from authlib.integrations.starlette_client import OAuth
from authlib.integrations.fastapi_oauth2 import AuthorizationServer
from itsdangerous import URLSafeTimedSerializer
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import User, OAuthAccount
from database.database import get_db
from config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token handling
security = HTTPBearer()

# OAuth setup
oauth = OAuth()

oauth.register(
    name='google',
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url='https://accounts.google.com/.well-known/openid_configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

oauth.register(
    name='github',
    client_id=settings.github_client_id,
    client_secret=settings.github_client_secret,
    access_token_url='https://github.com/login/oauth/access_token',
    authorize_url='https://github.com/login/oauth/authorize',
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'},
)

# Token serializer for email verification
token_serializer = URLSafeTimedSerializer(settings.secret_key)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    from jose import jwt

    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email"""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get user by ID"""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    """Authenticate user with email and password"""
    user = await get_user_by_email(db, email)
    if not user or not user.password_hash:
        return None
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not verified. Please check your email for verification link."
        )
    if not verify_password(password, user.password_hash):
        return None
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token"""
    from jose import JWTError, jwt

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(credentials.credentials, settings.secret_key, algorithms=[settings.algorithm])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await get_user_by_id(db, user_id=int(user_id))
    if user is None:
        raise credentials_exception
    return user


async def create_oauth_user(db: AsyncSession, provider: str, user_info: dict) -> User:
    """Create user from OAuth provider information"""
    # Create user
    user = User(
        email=user_info.get('email'),
        username=user_info.get('name') or user_info.get('login'),
        email_verified=True  # OAuth users are considered verified
    )
    db.add(user)
    await db.flush()

    # Create OAuth account record
    oauth_account = OAuthAccount(
        user_id=user.id,
        provider=provider,
        provider_user_id=str(user_info.get('id')),
        access_token=user_info.get('access_token'),
        refresh_token=user_info.get('refresh_token')
    )
    db.add(oauth_account)
    await db.commit()
    await db.refresh(user)

    return user


async def get_or_create_oauth_user(db: AsyncSession, provider: str, user_info: dict) -> User:
    """Get existing OAuth user or create new one"""
    # Check if OAuth account exists
    result = await db.execute(
        select(OAuthAccount)
        .where(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_user_id == str(user_info.get('id'))
        )
    )
    oauth_account = result.scalar_one_or_none()

    if oauth_account:
        # Update tokens
        oauth_account.access_token = user_info.get('access_token')
        oauth_account.refresh_token = user_info.get('refresh_token')
        await db.commit()

        # Get user
        user = await get_user_by_id(db, oauth_account.user_id)
        return user

    # Check if user exists by email
    email = user_info.get('email')
    if email:
        existing_user = await get_user_by_email(db, email)
        if existing_user:
            # Link OAuth account to existing user
            oauth_account = OAuthAccount(
                user_id=existing_user.id,
                provider=provider,
                provider_user_id=str(user_info.get('id')),
                access_token=user_info.get('access_token'),
                refresh_token=user_info.get('refresh_token')
            )
            db.add(oauth_account)
            existing_user.email_verified = True  # Mark as verified
            await db.commit()
            return existing_user

    # Create new user
    return await create_oauth_user(db, provider, user_info)

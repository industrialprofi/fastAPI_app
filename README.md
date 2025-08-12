# AI FastAPI Application

A FastAPI application with user authentication, rate limiting, and LLM integration that maintains conversation context.

## Features

- **User Authentication**: JWT-based authentication with registration and login
- **Rate Limiting**: Subscription-based rate limiting (Free, Pro, Enterprise plans)
- **LLM Integration**: OpenAI GPT integration with conversation context
- **Conversation Management**: Create, view, and delete conversations with message history
- **Database**: PostgreSQL with async SQLAlchemy

## Database Schema

The application implements the following tables:
- `users` - User accounts with email/password authentication
- `oauth_accounts` - OAuth2 integration (prepared for Google, GitHub, etc.)
- `subscription_plans` - Rate limiting plans (Free, Pro, Enterprise)
- `user_subscriptions` - User subscription assignments
- `request_logs` - API request logging for rate limiting
- `conversations` - Chat conversations
- `messages` - Individual messages within conversations

## Installation

1. **Clone and navigate to the project directory**

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**:
Copy `.env.example` to `.env` and configure:
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```
DATABASE_URL=postgresql+asyncpg://username:password@localhost/ai_fastapi_db
SECRET_KEY=your-secret-key-here
OPENAI_API_KEY=your-openai-api-key
```

4. **Set up PostgreSQL database**:
Create a PostgreSQL database and update the `DATABASE_URL` in your `.env` file.

## Running the Application

Start the FastAPI server:
```bash
python main.py
```

Or using uvicorn directly:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

Interactive API documentation: `http://localhost:8000/docs`

## API Endpoints

### Authentication
- `POST /auth/register` - Register a new user
- `POST /auth/login` - Login and get access token
- `GET /auth/me` - Get current user information

### Conversations
- `POST /conversations` - Create a new conversation
- `GET /conversations` - Get all user conversations
- `GET /conversations/{id}` - Get specific conversation with messages
- `DELETE /conversations/{id}` - Delete a conversation

### LLM Chat
- `POST /chat` - Send message to LLM and get response

### Subscriptions
- `GET /subscriptions/plans` - Get available subscription plans
- `GET /subscriptions/my-subscription` - Get current user's subscription

## Usage Examples

### 1. Register a new user
```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "testuser",
    "password": "password123"
  }'
```

### 2. Login
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'
```

### 3. Chat with LLM (new conversation)
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, how are you?",
    "new_conversation_title": "My First Chat"
  }'
```

### 4. Continue existing conversation
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Can you tell me more about that?",
    "conversation_id": 1
  }'
```

## Rate Limiting

The application includes three subscription tiers:

- **Free**: 5 requests/minute, 100 requests/day
- **Pro**: 20 requests/minute, 1,000 requests/day ($9.99)
- **Enterprise**: 100 requests/minute, 10,000 requests/day ($49.99)

New users automatically get a Free subscription.

## Project Structure

```
├── main.py              # FastAPI application and routes
├── models.py            # SQLAlchemy database models
├── schemas.py           # Pydantic schemas for request/response validation
├── database.py          # Database connection and session management
├── auth.py              # Authentication logic (JWT, password hashing)
├── rate_limit.py        # Rate limiting service
├── llm_service.py       # OpenAI LLM integration
├── config.py            # Application configuration
├── setup_db.py          # Database initialization script
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Development

The application uses:
- **FastAPI** for the web framework
- **SQLAlchemy** with async support for database ORM
- **Alembic** for database migrations
- **JWT** for authentication
- **OpenAI API** for LLM integration
- **PostgreSQL** as the database

## Security Features

- Password hashing with bcrypt
- JWT token-based authentication
- Rate limiting based on subscription plans
- SQL injection protection via SQLAlchemy ORM
- Input validation with Pydantic schemas

## Error Handling

The application includes comprehensive error handling for:
- Authentication errors (401)
- Rate limiting (429)
- Not found errors (404)
- Validation errors (422)
- Internal server errors (500)

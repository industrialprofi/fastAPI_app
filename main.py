from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.auth.router import router as auth_router
from routes.conversations.router import router as conversations_router
from routes.chats.router import router as chats_router
from routes.subscriptions.router import router as subscriptions_router

app = FastAPI(
    title="AI FastAPI App",
    description="FastAPI application with user authentication, OAuth, and LLM integration",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(conversations_router)
app.include_router(chats_router)
app.include_router(subscriptions_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

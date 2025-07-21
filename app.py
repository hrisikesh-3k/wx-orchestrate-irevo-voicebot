from datetime import datetime, timedelta
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import json
import logging
import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

from src.summary_chain import run_summary_sync, summary_chain
from src.constants import WELCOME_MESSAGE
from src.agents import VoiceEscalationAgent, MemoryManager
from src.dbio.db import init_db
from src.dbio.db import SessionLocal
from src.dbio.models import UserVerification
from src.dbio.session_history_manager import SessionHistoryManager
from src.utils.session import get_user_session
from src.logger import logger

# Load environment variables
load_dotenv()


# Pydantic models for request/response validation


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="User's message")
    session_id: Optional[str] = Field(None, description="Session identifier")

class ChatResponse(BaseModel):
    message: str
    show_escalation_buttons: bool = False
    escalation_reason: Optional[str] = None
    session_id: Optional[str] = None

class EscalationRequest(BaseModel):
    action: str = Field(..., description="Escalation action: 'talk_now' or 'schedule_callback'")
    session_id: str = Field(..., description="Session identifier")

class WebSocketMessage(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    session_id: Optional[str] = Field(None)
    message_type: str = Field(default="chat")

class ResetConversationRequest(BaseModel):
    session_id: str = Field(..., description="Session identifier")

class CallbackScheduleRequest(BaseModel):
    session_id: str = Field(..., description="Session identifier")
    phone_number: str = Field(..., description="Phone number for callback")
    preferred_time: str = Field(..., description="Preferred callback time")
    timezone: Optional[str] = Field(None, description="User's timezone")

# Global variables
agent: Optional[VoiceEscalationAgent] = None
executor = ThreadPoolExecutor(max_workers=10)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown events."""
    global agent
    
    logger.info("Starting up Banking Support API...")
    
    # Initialize single agent instance
    try:
        agent = VoiceEscalationAgent()
        logger.info("VoiceEscalationAgent initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize VoiceEscalationAgent: {e}")
        raise
    
    yield
    
    # Cleanup
    logger.info("Shutting down Banking Support API...")
    executor.shutdown(wait=True)

app = FastAPI(
    title="Banking Support API",
    description="AI-powered banking support with voice escalation capabilities",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration - be more restrictive in production
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Serve static files - relative to app.py location
static_dir = os.path.join(BASE_DIR, "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
else:
    logger.warning(f"Static directory not found: {static_dir}")

# Templates - relative to app.py location
templates_dir = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=templates_dir)


def get_or_create_session_id(provided_session_id: Optional[str] = None) -> str:
    """Get existing session ID or create a new one."""
    if provided_session_id:
        return provided_session_id
    return str(uuid.uuid4())

async def run_agent_chat(user_input: str, session_id: str) -> Dict[str, Any]:
    """Run agent chat synchronously in thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, agent.chat, user_input, session_id)

async def run_agent_chat_stream(user_input: str, session_id: str) -> Dict[str, Any]:
    """Run agent chat stream synchronously in thread pool."""
    loop = asyncio.get_event_loop()
    # Convert generator to single response for now
    result = await loop.run_in_executor(executor, agent.chat, user_input, session_id)
    return result

@app.get("/")
async def root(request: Request):
    """Serve the main chat interface."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/customer_chat_summary")
async def summarize_session():
    memory_manager = MemoryManager()

    messages = memory_manager.get_current_message_history()
    if not messages:
        raise HTTPException(status_code=404, detail="No chat history found for this session")

    response = run_summary_sync(messages)

    now_dt = datetime.now()
    

    # Get time 5 minutes ago (still datetime object)
    five_minutes_ago_dt = now_dt - timedelta(minutes=5)

    # Now format both to strings
    five_minutes_ago = five_minutes_ago_dt.strftime("%I:%M:%S %p")


    # Get time 5 minutes ago
    return {
        "name": response.get("name", ""),
        "policy_number": response.get("policy_number", ""),
        "summary": response.get("summary", ""),
        "date": datetime.now().isoformat(),
        "time": five_minutes_ago,
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "agent_initialized": agent is not None,
        "version": "1.0.0"
    }

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """REST endpoint for chat interactions."""
    try:
        # Get or create session ID
        # session_id = get_or_create_session_id(request.session_id)

        # # Generate session ID
        session_manager = SessionHistoryManager()
    
        session_id = session_manager.session_id
        # print(session.session_id)
        # logger.info(f"session id from ws endpoint: -- {session_id}")


        # logger.info(f"Chat request for session {session_id}: {request.query[:50]}...")
        
        if not agent:
            logger.error("Agent not initialized")
            raise HTTPException(status_code=503, detail="Service temporarily unavailable")
        
        # Run agent with session ID
        response = await run_agent_chat(request.query, session_id)
        
        logger.info(f"Agent response for session {session_id}: {response}")
        
        return ChatResponse(
            message=response.get("message", "I'm here to help!"),
            show_escalation_buttons=response.get("show_escalation_buttons", False),
            escalation_reason=response.get("escalation_reason"),
            session_id=session_id
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        session_id = get_or_create_session_id(request.session_id)
        return ChatResponse(
            message="I'm experiencing technical difficulties. Let me connect you with a human support agent.",
            show_escalation_buttons=True,
            escalation_reason="system_error",
            session_id=session_id
        )



@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time chat."""
    await websocket.accept()
    
    # Generate session ID
    session_manager = SessionHistoryManager()
    
    session_id = session_manager.session_id

    # session = get_user_session()
    # session_id = session.session_id
    # print(session.session_id)
    # logger.info(f"session id from ws endpoint: -- , {session_id}")


    # logger.info(f"WebSocket connection established: {session_id}")
    
    try:
        # Send welcome message
        await websocket.send_json({
            "message": WELCOME_MESSAGE,
            "role": "bot",
            "session_id": session_id
        })
        
        while True:
            try:
                # Receive message
                data = await asyncio.wait_for(websocket.receive_json(), timeout=300)  # 5 min timeout
                
                # Validate message
                try:
                    ws_message = WebSocketMessage(**data)
                except Exception as e:
                    await websocket.send_json({
                        "error": "Invalid message format",
                        "role": "system"
                    })
                    continue
                
                user_input = ws_message.message
                # Use provided session_id or the WebSocket session_id

                current_session_id = ws_message.session_id or session_id
                
                # logger.info(f"WebSocket message for session {current_session_id}: {user_input[:50]}...")
                
                # Check agent availability
                if not agent:
                    await websocket.send_json({
                        "error": "Service temporarily unavailable",
                        "role": "system"
                    })
                    continue
                
                # Process message with session ID
                response = await run_agent_chat(user_input, current_session_id)
                
                # print("Agent response:", response)
                logger.info(f"Agent response for session {current_session_id}: {response}")
                # Send response
                await websocket.send_json({
                    "message": response.get("message", "I'm here to help!"),
                    "role": "bot",
                    "show_escalation_buttons": response.get("show_escalation_buttons", False),
                    "escalation_reason": response.get("escalation_reason"),
                    "session_id": current_session_id
                })
                
            except asyncio.TimeoutError:
                logger.info(f"WebSocket timeout for session: {session_id}")
                await websocket.send_json({
                    "message": "Session timeout. Please refresh if you need continued assistance.",
                    "role": "system"
                })
                break
                
            except json.JSONDecodeError:
                await websocket.send_json({
                    "error": "Invalid JSON format",
                    "role": "system"
                })
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        try:
            await websocket.send_json({
                "error": "Internal server error",
                "role": "system"
            })
        except:
            pass
    finally:
        # Cleanup session
        if agent:
            try:
                agent.cleanup_session(session_id)
            except Exception as e:
                logger.error(f"Error cleaning up session {session_id}: {e}")



@app.get("/sessions/{session_id}/status")
async def get_session_status(session_id: str):
    """Get session status including escalation state."""
    try:
        if not agent:
            raise HTTPException(status_code=503, detail="Service temporarily unavailable")
        
        is_escalated = agent.is_escalated(session_id)
        history_count = len(agent.get_conversation_history(session_id))
        
        return {
            "session_id": session_id,
            "is_escalated": is_escalated,
            "message_count": history_count,
            "status": "escalated" if is_escalated else "active"
        }
    except Exception as e:
        logger.error(f"Error getting session status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve session status")

@app.post("/sessions/{session_id}/cleanup")
async def cleanup_session(session_id: str):
    """Clean up resources for a specific session."""
    try:
        if not agent:
            raise HTTPException(status_code=503, detail="Service temporarily unavailable")
        
        # Clean up session resources
        agent.cleanup_session(session_id)
        logger.info(f"Session cleaned up: {session_id}")
        
        return {
            "message": "Session cleaned up successfully",
            "session_id": session_id
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to cleanup session")

@app.get("/sessions/active")
async def get_active_sessions():
    """Get list of active sessions."""
    try:
        if not agent:
            raise HTTPException(status_code=503, detail="Service temporarily unavailable")
        
        active_sessions = agent.get_active_sessions()
        return {
            "active_sessions": active_sessions,
            "count": len(active_sessions)
        }
        
    except Exception as e:
        logger.error(f"Error getting active sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve active sessions")

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    logger.error(f"HTTP error {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "status_code": 500}
    )

# Additional utility endpoints
@app.get("/metrics")
async def get_metrics():
    """Get system metrics."""
    try:
        if not agent:
            raise HTTPException(status_code=503, detail="Service temporarily unavailable")
        
        metrics = {
            "active_sessions": len(agent.get_active_sessions()) if hasattr(agent, 'get_active_sessions') else 0,
            "escalated_sessions": len([s for s in agent.get_active_sessions() if agent.is_escalated(s)]) if hasattr(agent, 'get_active_sessions') else 0,
            "executor_queue_size": executor._work_queue.qsize() if hasattr(executor, '_work_queue') else 0,
            "agent_initialized": agent is not None,
        }
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")

if __name__ == "__main__":
    import uvicorn
    
    # Configuration
    # host = os.getenv("HOST", "0.0.0.0")
    # port = int(os.getenv("PORT", 8000))
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8080,
        # reload=True,
        # log_level="info",

    )
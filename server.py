import asyncio
import json
import subprocess
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from debate_graph import create_debate_app

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="static")

@app.get("/")
async def get_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

import requests

@app.get("/models")
async def get_models():
    models = []
    
    # Get Ollama models
    try:
        response = requests.get('http://192.168.0.2:11434/api/tags', timeout=2)
        if response.status_code == 200:
            data = response.json()
            for model in data.get('models', []):
                models.append({"name": model['name'], "provider": "ollama"})
    except Exception as e:
        print(f"Error listing Ollama models: {e}")

    # Add Gemini models
    gemini_models = [
        "gemini-3-pro",
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-pro",
        "gemini-1.5-flash"
    ]
    for m in gemini_models:
        models.append({"name": m, "provider": "google"})

    return JSONResponse(content={"models": models})

import uuid

# Store active debate sessions
sessions = {}

@app.post("/start_debate")
async def start_debate_endpoint(request: Request):
    data = await request.json()
    topic = data.get("topic")
    model = data.get("model", "qwq")
    provider = data.get("provider", "ollama")
    google_api_key = data.get("google_api_key")
    
    print(f"Starting debate session with topic: {topic}, model: {model}, provider: {provider}")
    
    # Create a new app instance
    debate_app = create_debate_app(model, provider, google_api_key)
    
    # Generate session ID
    session_id = str(uuid.uuid4())
    
    # Store session
    sessions[session_id] = {
        "app": debate_app,
        "topic": topic,
        "turn_count": 0
    }
    
    return JSONResponse(content={"session_id": session_id})

@app.get("/next_turn")
async def next_turn(session_id: str):
    if session_id not in sessions:
        return JSONResponse(content={"error": "Session not found"}, status_code=404)
    
    session = sessions[session_id]
    debate_app = session["app"]
    topic = session["topic"]
    
    async def event_generator():
        # Configuration for the thread
        config = {"configurable": {"thread_id": session_id}, "recursion_limit": 150}
        
        inputs = None
        if session["turn_count"] == 0:
            print(f"Session {session_id}: First turn, providing inputs.")
            inputs = {
                "history": [],
                "current_topic": topic
            }
        else:
            print(f"Session {session_id}: Resuming turn {session['turn_count']}.")
        
        try:
            # Use astream_events
            # If inputs is None, it resumes from interrupt
            event_count = 0
            async for event in debate_app.astream_events(inputs, version="v2", config=config):
                event_count += 1
                kind = event["event"]
                
                # Log ALL events for debugging
                if event_count <= 10 or kind in ["on_chat_model_stream", "on_chain_stream"]:
                    print(f"[DEBUG] Event #{event_count}: {kind}")
                
                # Stream tokens - handle both event types for cross-platform compatibility
                if kind == "on_chat_model_stream":
                    # Windows/direct streaming approach
                    content = event["data"]["chunk"].content
                    print(f"[DEBUG] Token content (chat_model): {repr(content)}")
                    if content:
                        # Determine role from node name
                        node_name = event.get("metadata", {}).get("langgraph_node", "")
                        role = "unknown"
                        if node_name == "moderator":
                            role = "moderator"
                        elif node_name == "debater_A":
                            role = "proponent"
                        elif node_name == "debater_B":
                            role = "opponent"
                        
                        if role != "unknown":
                            data = json.dumps({
                                "type": "token",
                                "role": role,
                                "content": content
                            })
                            print(f"[DEBUG] Emitting token for {role}: {content[:20]}...")
                            yield f"data: {data}\n\n"
                        else:
                            print(f"[DEBUG] Token skipped - unknown role for node: {node_name}")
                
                elif kind == "on_chain_stream":
                    # RPi/alternative streaming approach
                    chunk = event["data"].get("chunk")
                    node_name = event.get("metadata", {}).get("langgraph_node", "")
                    
                    print(f"[DEBUG] on_chain_stream - node: {node_name}, chunk type: {type(chunk)}")
                    
                    if chunk:
                        # Try different ways to get content
                        content = None
                        
                        # Method 1: Direct attribute
                        if hasattr(chunk, 'content'):
                            content = chunk.content
                            print(f"[DEBUG] Found content via .content: {repr(content)}")
                        
                        # Method 2: Dictionary key
                        elif isinstance(chunk, dict) and 'content' in chunk:
                            content = chunk['content']
                            print(f"[DEBUG] Found content via ['content']: {repr(content)}")
                        
                        # Method 3: Inspect the chunk structure
                        else:
                            print(f"[DEBUG] Chunk structure: {chunk}")
                            if hasattr(chunk, '__dict__'):
                                print(f"[DEBUG] Chunk attributes: {chunk.__dict__}")
                        
                        if content:
                            role = "unknown"
                            if node_name == "moderator":
                                role = "moderator"
                            elif node_name == "debater_A":
                                role = "proponent"
                            elif node_name == "debater_B":
                                role = "opponent"
                            
                            if role != "unknown":
                                data = json.dumps({
                                    "type": "token",
                                    "role": role,
                                    "content": content
                                })
                                print(f"[DEBUG] Emitting token for {role}: {content[:20]}...")
                                yield f"data: {data}\n\n"

                # Handle decision/stop (check state updates)
                elif kind == "on_chain_end":
                    node_name = event.get("metadata", {}).get("langgraph_node")
                    
                    if node_name in ["moderator", "debater_A", "debater_B"]:
                        # Emit turn_end event
                        print(f"[DEBUG] Emitting turn_end for {node_name}")
                        yield f"data: {json.dumps({'type': 'turn_end', 'role': node_name})}\n\n"

                    if node_name == "moderator":
                        # Check if moderator decided to stop
                        output = event["data"].get("output")
                        if output and isinstance(output, dict) and output.get("decision") == "stop":
                            print(f"[DEBUG] Emitting end event")
                            yield f"data: {json.dumps({'type': 'end'})}\n\n"
            
            print(f"[DEBUG] Total events processed: {event_count}")
            # Increment turn count after successful stream
            session["turn_count"] += 1
            print(f"[DEBUG] Turn {session['turn_count']} completed")

        except Exception as e:
            print(f"Error in stream: {e}")
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        
        # Signal that this turn's stream is done (client should close)
        print(f"[DEBUG] Emitting stream_end")
        yield f"data: {json.dumps({'type': 'stream_end'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

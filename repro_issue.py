import asyncio
import uuid
from debate_graph import create_debate_app

async def main():
    print("Starting reproduction script...")
    
    # 1. Create App
    topic = "AI Safety"
    model = "qwq:latest" 
    # If user doesn't have llama3, this might fail. 
    # But I saw 'llama3' not found error in logs, so I know they have ollama running.
    # I'll use 'qwq' which is default, or 'llama3.2' if available.
    # Let's assume 'llama3' for now as in the curl test.
    provider = "ollama"
    
    print(f"Creating app with model={model}, provider={provider}")
    app = create_debate_app(model, provider)
    
    session_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": session_id}, "recursion_limit": 150}
    
    # 2. First Turn
    print("\n--- Turn 1 (Start) ---")
    inputs = {
        "history": [],
        "current_topic": topic
    }
    
    try:
        async for event in app.astream_events(inputs, version="v2", config=config):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    print(f"Token: {content}", end="", flush=True)
            elif kind == "on_chain_end":
                node_name = event.get("metadata", {}).get("langgraph_node")
                if node_name:
                    print(f"\nNode finished: {node_name}")
    except Exception as e:
        print(f"\nError in Turn 1: {e}")

    print("\n\n--- Turn 1 Finished ---")
    
    # 3. Check State
    snapshot = await app.aget_state(config)
    print(f"Next step: {snapshot.next}")
    
    # 4. Second Turn (Resume)
    print("\n--- Turn 2 (Resume) ---")
    try:
        async for event in app.astream_events(None, version="v2", config=config):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    print(f"Token: {content}", end="", flush=True)
            elif kind == "on_chain_end":
                node_name = event.get("metadata", {}).get("langgraph_node")
                if node_name:
                    print(f"\nNode finished: {node_name}")
    except Exception as e:
        print(f"\nError in Turn 2: {e}")

if __name__ == "__main__":
    asyncio.run(main())

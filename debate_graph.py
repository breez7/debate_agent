from langgraph.graph import END, StateGraph
from typing import Dict, TypedDict, List
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google.api_core.exceptions import ResourceExhausted

# 상태 정의
class DebateState(TypedDict):
    history: List[str]
    current_topic: str
    decision: str # Added decision to state for easier access

MAX_TURNS = 100

# 사회자 프롬프트 템플릿
MODERATOR_INIT_PROMPT = """당신은 전문 토론 사회자입니다. 
주제: {topic}

다음 규칙을 엄격히 지키세요:
1. 양측의 입장을 명확히 하고, 토론의 쟁점을 제시하세요.
2. 토론이 활발하게 이루어질 수 있도록 흥미로운 소주제를 던지세요.
3. 첫 발언이므로 토론자들에게 발언 기회를 넘기세요.
4. 절대 토론을 바로 종료하지 마세요.

출력 형식:
[사회자 발언 내용]
Decision: continue
"""

MODERATOR_PROMPT = """당신은 전문 토론 사회자입니다. 
주제: {topic}

다음 규칙을 엄격히 지키세요:
1. 주제에서 벗어난 발언이 있으면 즉시 중단하고 주제로 돌아가도록 지시하세요.
2. 동일한 주장의 반복이 너무 많이 발생하면 새로운 관점을 제시하거나 다음 쟁점으로 넘어가세요.
3. 건전한 토론 환경을 유지하기 위해 공격적인 발언 시 경고하세요.
4. 토론이 원활히 진행되지 않는다면 주제에서의 소주제를 제시하여 토론을 이어가도록 유도하세요.
5. 토론이 충분히 무르익었거나(최소 10회 이상 왕복), 더 이상 새로운 논점이 나오지 않을 때만 종료를 선언하세요.
6. 그 전까지는 토론을 계속 진행시키세요.

지난 발언 기록:
{history}

다음 발언 전에 다음 중 하나의 판단을 내려야 합니다. 반드시 마지막 줄에 Decision: [continue/instruction/stop] 형식을 포함하세요.
- 계속 진행 (특별한 개입 필요 없음): 'continue'
- 의사 진행 발언 (개입 필요): 'instruction'
- 토론 종료: 'stop'

출력 예시:
[사회자 발언 또는 평가 내용]
Decision: continue
"""

# 토론자 프롬프트 템플릿
DEBATER_PROMPT = """당신은 {name} 입장의 토론자입니다. 
주제: {topic}

다음 지침을 따라 토론에 참여하세요:
1. 상대방의 논리를 날카롭게 분석하고 반박하세요.
2. 자신의 주장을 뒷받침할 구체적인 근거와 예시를 제시하세요.
3. 상대방의 의견 중 타당한 부분은 인정하되, 핵심 쟁점에서는 물러서지 마세요.
4. 감정적인 대응보다는 논리적인 설득을 우선시하세요.
5. 사회자의 지시가 있다면 이를 충실히 따르세요.
6. 상대방을 존중하는 태도를 유지하세요.

지난 발언 기록:
{recent_history}

사회자의 지시사항:
{moderator_instruction}

당신의 차례입니다. 간결하고 강력하게 발언하세요:"""

def get_last_instructions(history):
    for msg in reversed(history):
        if "사회자:" in msg:
            content = msg.split("사회자:")[1].strip()
            # Remove Decision line if present in history
            if "Decision:" in content:
                content = content.split("Decision:")[0].strip()
            return content
    return ""

def create_debate_app(model_name: str, provider: str, api_key: str = None):
    
    if provider == 'google':
        if not api_key and "GOOGLE_API_KEY" not in os.environ:
            print("Warning: GOOGLE_API_KEY not found.")
        
        llm = ChatGoogleGenerativeAI(model=model_name, temperature=0.7, google_api_key=api_key)
    else:
        # Default to Ollama
        llm = ChatOllama(base_url='http://192.168.0.2:11434', model=model_name)

    # Retry configuration
    # Wait exponentially: 4s, 8s, 16s... up to 60s. Stop after 5 attempts.
    # Retry specifically on ResourceExhausted (429)
    @retry(
        retry=retry_if_exception_type(ResourceExhausted),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(10)
    )
    async def invoke_llm(prompt):
        content = ""
        async for chunk in llm.astream(prompt):
            content += chunk.content
        return content

    async def moderator_node(state: DebateState):
        history_str = "\n".join(state["history"])
        
        # Turn limit check
        if len(state['history']) >= MAX_TURNS:
            instruction = "토론이 최대 턴 수에 도달하여 종료합니다. 모두 수고하셨습니다."
            state["history"].append(f"사회자: {instruction}")
            return {"decision": "stop", "history": state["history"]}

        # 사회자 판단
        if len(state['history']) == 0:
            content = await invoke_llm(
                MODERATOR_INIT_PROMPT.format(
                    topic=state["current_topic"]
                )
            )
        else:
            content = await invoke_llm(
                MODERATOR_PROMPT.format(
                    topic=state["current_topic"],
                    history=history_str
                )
            )
        
        decision = 'continue' # Default to continue
        instruction = ''
        
        # Handle think blocks if present (common in some models)
        if '</think>' in content:
            content_after_think = content[content.find('</think>')+8:].strip()
        else:
            content_after_think = content

        # Parse Decision
        lines = content_after_think.strip().split('\n')
        last_line = lines[-1].strip()
        
        if 'Decision:' in last_line:
            decision_part = last_line.split('Decision:')[1].strip().lower()
            if 'stop' in decision_part:
                decision = 'stop'
            elif 'instruction' in decision_part:
                decision = 'instruction'
            else:
                decision = 'continue'
            
            # Remove the decision line from the content to be displayed
            instruction = "\n".join(lines[:-1]).strip()
        else:
            # Fallback logic if no explicit decision
            if 'stop' in content_after_think.lower() and len(state['history']) > 10:
                decision = 'stop'
            elif len(state['history']) == 0:
                decision = 'instruction'
            
            instruction = content_after_think

        # Force continue if too short
        if decision == 'stop' and len(state['history']) < 6:
             decision = 'continue'
             instruction += "\n(아직 토론이 충분하지 않아 계속 진행합니다.)"

        state["history"].append(f"사회자: {instruction}")
        return {"decision": decision, "history": state["history"]}

    def debater_node_factory(debater_name: str):
        async def node_func(state: DebateState):
            recent_history = "\n".join(state["history"])
            instruction = get_last_instructions(state["history"])
            
            prompt = DEBATER_PROMPT.format(
                name=debater_name,
                topic=state["current_topic"],
                recent_history=recent_history,
                moderator_instruction=instruction
            )

            content = await invoke_llm(prompt)
            
            if '</think>' in content:
                cleaned_response = content[content.find('</think>')+8:].strip()
            else:
                cleaned_response = content.strip()
            
            state["history"].append(f"{debater_name}: {cleaned_response}")
            return {"history": state["history"]}
        return node_func

    # 그래프 구성
    workflow = StateGraph(DebateState)

    # 노드 추가
    workflow.add_node("moderator", moderator_node)
    workflow.add_node("debater_A", debater_node_factory("찬성"))
    workflow.add_node("debater_B", debater_node_factory("반대"))

    # 엣지 설정
    workflow.add_edge("debater_A", "debater_B")
    workflow.add_edge("debater_B", "moderator")

    # 조건부 분기 설정
    def decide_continue(state):
        return "end" if state.get("decision") == "stop" else "continue"

    workflow.add_conditional_edges(
        "moderator",
        decide_continue,
        {
            "continue": "debater_A",
            "end": END
        }
    )

    workflow.set_entry_point("moderator")
    
    # Use MemorySaver for checkpointing
    from langgraph.checkpoint.memory import MemorySaver
    checkpointer = MemorySaver()
    
    # Compile with interrupts and checkpointer
    app = workflow.compile(
        checkpointer=checkpointer,
        interrupt_after=["moderator", "debater_A", "debater_B"]
    )
    return app
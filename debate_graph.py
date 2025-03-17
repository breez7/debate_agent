from langgraph.graph import END, StateGraph
from typing import Dict, TypedDict, List
from langchain_ollama import ChatOllama
import os

# Ollama 설정 (로컬에서 실행 필요)
# os.environ["OLLAMA_HOST"] = "http://192.168.0.2:11434"

# 상태 정의
class DebateState(TypedDict):
    history: List[str]
    current_topic: str

# 모델 초기화
model = 'qwq'
# model = 'gemma3:27b-it-q4_K_M'
debate_llm = ChatOllama(base_url='http://192.168.0.2:11434', model=model)
moderator_llm = ChatOllama(base_url='http://192.168.0.2:11434', model=model)
# debate_llm = Ollama(model="llama2")
# moderator_llm = Ollama(model="llama2")

# 사회자 프롬프트 템플릿

MODERATOR_INIT_PROMPT = """당신은 전문 토론 사회자입니다. 다음 규칙을 엄격히 지키세요: 
1. 주제({topic})에 대해서 어떻게 해야 좋은 토론이 될 수 있을지 고민한다.
2. 토론자들에게 주제를 충분히 설명하고 시작 토론이 될 수 있는 소주제를 토론자들에게 전달한다.

"""

MODERATOR_PROMPT = """당신은 전문 토론 사회자입니다. 다음 규칙을 엄격히 지키세요:
1. 주제({topic})에서 벗어난 발언이 있으면 즉시 중단하고 주제로 돌아가도록 지시
2. 동일한 주장의 반복이 너무 많이 발생하면 의사 진행 발언 지시
3. 건전한 토론 환경을 유지하기 위해 공격적인 발언 시 경고
4. 토론이 원활히 진행되지 않는다면 주제에서의 소주제를 제시하여 토론을 이어가도록 유도
5. 토론이 원활히 진행되도록 의사 진행 발언은 소극적으로 한다.

지난 발언 기록:
{history}

다음 발언 전에 다음 중 하나의 판단을 해야 합니다:
- 계속 진행: 'continue'
- 의사 진행 발언: 'instruction'
- 토론 종료: 'stop'
결과와 그 이유를 답변해주세요."""

# 토론자 프롬프트 템플릿
DEBATER_PROMPT = """당신은 {name} 입장의 토론자입니다. 사회자의 규칙을 준수하며 다음 주제에 대해 토론하세요. 토론을 진행하면서 상대방과의 의견 차이를 좁힐수 있도록 노력해주세요.상대방을 부르는 군더더기는 제외해주세요. 상대방의 의견이 설득력이 있다면 상대방의 의견에 동조해주세요.:
주제: {topic}

지난 발언 기록:
{recent_history}

사회자의 최종 지시사항:
{moderator_instruction}

당신의 차례입니다. 간결하고 논리적으로 반박 또는 주장을 펼치세요:"""

def get_last_instructions(history):
    for msg in reversed(history):
        if "사회자:" in msg:
            return msg.split(":")[1].strip()
    return ""

def moderator_node(state: DebateState):
    history_str = "\n".join(state["history"])

    print('\n[사회자] : ')

    # 사회자 판단
    if len(state['history']) == 0:
        response = moderator_llm.invoke(
            MODERATOR_INIT_PROMPT.format(
                topic=state["current_topic"]
            )
        )
    else:
        response = moderator_llm.invoke(
            MODERATOR_PROMPT.format(
                topic=state["current_topic"],
                history=history_str
            )
        )
    # print(response)
    
    decision = '' 
    instruction = ''
    if 'continue' in response.content.lower():
        decision = 'continue'
        instruction = '계속 진행'
    elif 'instruction' in response.content.lower():
        decision = 'instruction'
        instruction = response.content[response.content.find('</think>')+10:][response.content.find('\n')+1:]
    elif len(state['history']) == 0:
        decision = 'instruction'
        instruction = response.content[response.content.find('</think>')+10:]
    else:
        decision = 'stop'
        instruction = response.content[response.content.find('</think>')+10:][response.content.find('\n')+1:]

    
    state["history"].append(f"사회자: {instruction}")
    print(f"{instruction}")

    return {"decision": decision, **state}

def debater_node(debater_name: str):
    def node_func(state: DebateState):
        recent_history = "\n".join(state["history"])
        instruction = get_last_instructions(state["history"])
        
        prompt = DEBATER_PROMPT.format(
            name=debater_name,
            topic=state["current_topic"],
            recent_history=recent_history,
            moderator_instruction=instruction
        )

        print(f'\n$$$[{debater_name}] : ')     
        response = debate_llm.invoke(prompt)
        cleaned_response = response.content[response.content.find('</think>')+10:].strip()
        
        state["history"].append(f"{debater_name}: {cleaned_response}")
        print(f"{cleaned_response}")
        return state
    return node_func

# 그래프 구성
workflow = StateGraph(DebateState)

# 노드 추가
workflow.add_node("moderator", moderator_node)
workflow.add_node("debater_A", debater_node("찬성"))
workflow.add_node("debater_B", debater_node("반대"))

# 엣지 설정
workflow.add_edge("debater_A", "debater_B")
workflow.add_edge("debater_B", "moderator")

# 조건부 분기 설정
def decide_continue(state):
    return "end" if state["decision"] == "stop" else "continue"

workflow.add_conditional_edges(
    "moderator",
    decide_continue,
    {
        "continue": "debater_A",
        "end": END
    }
)

workflow.set_entry_point("moderator")
app = workflow.compile()
app.recurision_limit = 100

# 토론 실행 함수
def run_debate(topic: str):
    print(f"\n{'='*30}\n토론 주제: {topic}\n{'='*30}")
    app.invoke({
        "history": [],
        "current_topic": topic
    })

# 실행 예제
if __name__ == "__main__":
    # run_debate("재생 에너지만으로 화석 연료를 완전히 대체할 수 있을까요?")
    # run_debate("피자에 파인애플을 넣는것에 어떻게 생각하시나요?")
    run_debate("관우와 여포가 싸우면 관우가 이긴다.")
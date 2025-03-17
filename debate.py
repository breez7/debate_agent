# from langchain.chat_models import ChatOpenAI
from langchain_ollama import ChatOllama

from langchain.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    AIMessagePromptTemplate
)
from langchain.schema import (
    AIMessage,
    HumanMessage,
    SystemMessage
)

debate_history = []
class DebateAgent:
    def __init__(self, name, role, llm, topic):
        self.name = name
        self.role = role
        self.llm = llm
        self.topic = topic
        # self.debate_history = []

    def generate_response(self, statement):
        messages = [
            SystemMessage(content=f"You are {self.name}, a debater with the role: {self.role}. You are debating on the topic: {self.topic}."),
        ]

        # 대화 기록 추가 (필요한 경우)
        for prev_speaker, prev_statement in debate_history:
            if prev_speaker == self.name:
                messages.append(AIMessage(content=prev_statement))
            else:
                messages.append(HumanMessage(content=prev_statement))

        response = self.llm(messages).content
        debate_history.append((self.name, response))
        return response


class Moderator:
    def __init__(self, llm, topic):
        self.llm = llm
        self.topic = topic

    def generate_initial_statement(self):
      messages = [
            SystemMessage(content=f"You are a debate moderator. The topic is: {self.topic}.  Introduce the topic and ask the first debater to begin."),
            HumanMessage(content="Start the debate.")
        ]
      return self.llm(messages).content


    def keep_on_topic(self, statement):
        # 주제에서 벗어났는지 판단 (간단한 예시)
        messages = [
            SystemMessage(content=f"You are a debate moderator. Determine if the following statement is on topic: '{self.topic}'.  Answer very briefly, 'On topic' or 'Off topic'."),
            HumanMessage(content=statement)

        ]
        response = self.llm(messages).content

        if "Off topic" in response:
            return "Please stay on topic."  # 더 정교한 제어 가능
        return "" #  On Topic

    def moderate(self, statement1, statement2):
        feedback1 = self.keep_on_topic(statement1)
        feedback2 = self.keep_on_topic(statement2)

        feedback = ""
        if feedback1:
            feedback += f"Debater 1: {feedback1}\n"
        if feedback2:
            feedback += f"Debater 2: {feedback2}\n"

        if not feedback: # 둘다 on topic이면 중재자가 개입할 필요가 없다.
            return ""

        messages = [
              SystemMessage(content=f"You are a debate moderator. Provide concise feedback to the debaters, addressing any off-topic comments. The topic is '{self.topic}'."),
              HumanMessage(content=feedback)
        ]

        return self.llm(messages).content


def run_debate(topic, agent1_role, agent2_role, num_rounds=3, openai_api_key="YOUR_API_KEY"):

    # LLM 설정 (OpenAI API Key 필요)
    # llm = ChatOpenAI(temperature=0.7, openai_api_key=openai_api_key)
    # llm = ChatOllama(base_url='http://192.168.0.2:11434', model='qwq')
    llm = ChatOllama(base_url='http://192.168.0.2:11434', model='gemma3:27b-it-q4_K_M')

    # 토론 에이전트 및 사회자 생성
    agent1 = DebateAgent(name="철수", role=agent1_role, llm=llm, topic=topic)
    agent2 = DebateAgent(name="영희", role=agent2_role, llm=llm, topic=topic)
    moderator = Moderator(llm=llm, topic=topic)

    # 토론 시작
    print("Moderator:", moderator.generate_initial_statement())
    statement = "My opening statement is that " + agent1.generate_response("Please provide your opening statement.")  # 초기 발언 요청.
    print(f"\n&&&{agent1.name}:", statement)


    for i in range(num_rounds):
        # Agent 2 발언
        response2 = agent2.generate_response(statement)
        print(f"\n\n##{agent2.name}:", response2)


        # Agent 1 발언
        response1 = agent1.generate_response(response2)
        print(f"\n\n&&&{agent1.name}:", response1)

        # 사회자 개입 (필요한 경우)
        moderator_feedback = moderator.moderate(response1, response2)

        if moderator_feedback:
            print("Moderator:", moderator_feedback)
            #  사회자가 개입을 했다면,  다시 기회를 준다.
            response1 = agent1.generate_response("Please respond, keeping the moderator's feedback in mind.")
            print(f"\n**{agent1.name}:", response1)


        statement = response1  # 다음 라운드를 위해 마지막 발언 업데이트

    print("Moderator: The debate has concluded.")



if __name__ == "__main__":
    topic = "매트릭스에서 파란약과 빨간약중 어떤것을 선택하시겠습니까?, 모든 답변은 한글로 해주세요."
    agent1_role = "당연히 빨간약을 선택한다. 비판적이며 비아냥 거린다."
    agent2_role = "당연히 파란약을 선택한다. 비판적이며 비아냥 거린다."

    # 실제 OpenAI API Key로 바꿔주세요.  (환경변수 사용하는 것이 좋습니다.)
    run_debate(topic, agent1_role, agent2_role, num_rounds=4, openai_api_key="YOUR_OPENAI_API_KEY")
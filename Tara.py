import os
import time
import random
import json
import difflib
import platform

# --- 운영체제별 소리 설정 ---
SYSTEM_OS = platform.system()

def play_sound(type):
    """
    type: 'correct' (딩동), 'wrong' (땡), 'level_up' (빠라바밤)
    Windows: winsound 사용
    Mac/Linux: 단순 비프음(\a) 또는 무음 처리 (오류 방지)
    """
    if SYSTEM_OS == "Windows":
        import winsound
        if type == 'correct':
            # 딩~동 (높은 미 -> 높은 도)
            winsound.Beep(1318, 150) # E6
            winsound.Beep(1046, 200) # C6
        elif type == 'wrong':
            # 띡 (낮은 음)
            winsound.Beep(300, 150)
        elif type == 'high_score':
            # 빠라바밤 (축하음)
            winsound.Beep(523, 150) # 도
            winsound.Beep(659, 150) # 미
            winsound.Beep(783, 150) # 솔
            winsound.Beep(1046, 400) # 높은 도
    else:
        # Mac/Linux는 간단히 시스템 비프음 출력
        if type == 'correct' or type == 'wrong':
            print('\a', end='', flush=True)

# --- 데이터 저장소 ---
SHORT_SENTENCES = [
    "가는 말이 고와야 오는 말이 곱다.",
    "소 잃고 외양간 고친다.",
    "천 리 길도 한 걸음부터.",
    "지렁이도 밟으면 꿈틀한다.",
    "원숭이도 나무에서 떨어질 때가 있다.",
    "낮말은 새가 듣고 밤말은 쥐가 듣는다.",
    "호랑이에게 물려가도 정신만 차리면 산다.",
    "티끌 모아 태산.",
    "열 번 찍어 안 넘어가는 나무 없다.",
    "개천에서 용 난다."
]

LONG_SENTENCES = [
    """계절이 지나가는 하늘에는 가을로 가득 차 있습니다.
나는 아무 걱정도 없이 가을 속의 별들을 다 헤일 듯합니다.""",
    """나를 키운 건 팔할이 바람이었다.
세상은 가도가도 부끄럽기만 하더라."""
]

GAME_WORDS = ["한메타자", "컴퓨터", "대한민국", "프로그래밍", "파이썬", "인공지능", 
              "알고리즘", "데이터", "키보드", "모니터", "마우스", "스마트폰", 
              "갤럭시", "아이폰", "네트워크", "보안", "클라우드", "서버", "비트코인"]

DATA_FILE = "typing_records.json"

# --- 유틸리티 함수 ---
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def load_records():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"short_best": 0, "game_best": 0, "total_typed": 0}

def save_records(records):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=4)

def get_accuracy(original, user_input):
    if not user_input: return 0
    matcher = difflib.SequenceMatcher(None, original, user_input)
    return round(matcher.ratio() * 100, 1)

def calculate_cpm(text, elapsed_time):
    if elapsed_time <= 0: return 0
    adjusted_len = len(text) * 2.5 
    cpm = (adjusted_len / elapsed_time) * 60
    return int(cpm)

# --- 메인 클래스 ---
class HanmeTyping:
    def __init__(self):
        self.records = load_records()
    
    def print_header(self, title):
        clear_screen()
        print("="*50)
        print(f"      한메타자연습 - {title}")
        print("="*50)
        print(f"★ 단문 최고: {self.records.get('short_best', 0)} 타 | ★ 게임 최고: {self.records.get('game_best', 0)} 점")
        print("-" * 50)

    def short_practice(self):
        while True:
            self.print_header("단문 연습")
            sentence = random.choice(SHORT_SENTENCES)
            print(f"\n[제시어]: {sentence}")
            print("\n(뒤로 가려면 'q' 입력)")
            
            start_time = time.time()
            user_input = input("[입력]  : ")
            end_time = time.time()
            
            if user_input.lower() == 'q': break
            
            elapsed = end_time - start_time
            acc = get_accuracy(sentence, user_input)
            speed = calculate_cpm(user_input, elapsed)
            
            print(f"\n>> 속도: {speed} 타/분 | 정확도: {acc}%")
            
            # 정확도 100%일 때 딩동 소리
            if acc == 100:
                play_sound('correct')
                print("완벽합니다! ♪")
            elif acc < 50:
                play_sound('wrong')
            
            if acc >= 90 and speed > self.records['short_best']:
                self.records['short_best'] = speed
                play_sound('high_score') # 신기록 축하음
                print("★ 신기록 달성! ★")
                save_records(self.records)
            
            input("\n[Enter] 다음 문장...")

    def run_text_practice(self, title, lines):
        total_speed = 0
        total_acc = 0
        count = 0
        
        for i, line in enumerate(lines):
            clean_line = line.strip()
            if not clean_line: continue

            self.print_header(title)
            print(f"진행 상황: {i+1} / {len(lines)} 줄\n")
            print(f"[문장]: {clean_line}")
            print("(중단: 'qq')")
            
            start_time = time.time()
            user_input = input("[입력]: ")
            end_time = time.time()
            
            if user_input.lower() == 'qq':
                print("\n중단합니다.")
                break
            
            elapsed = end_time - start_time
            acc = get_accuracy(clean_line, user_input)
            speed = calculate_cpm(user_input, elapsed)
            
            # 소리 효과
            if acc == 100:
                play_sound('correct')
            elif acc < 50:
                play_sound('wrong')

            total_speed += speed
            total_acc += acc
            count += 1
            
            print(f"\n>> 구간 속도: {speed} 타 | 정확도: {acc}%")
            time.sleep(0.3)

        if count > 0:
            avg_speed = int(total_speed / count)
            avg_acc = round(total_acc / count, 1)
            print("\n" + "="*30)
            print(f"평균 속도: {avg_speed} 타 | 평균 정확도: {avg_acc}%")
            if avg_acc >= 95:
                play_sound('high_score')
                print("정말 훌륭한 실력입니다!")
            input("메뉴로 돌아가려면 Enter...")

    def long_practice(self):
        text = random.choice(LONG_SENTENCES)
        lines = text.split('\n')
        self.run_text_practice("장문 연습 (기본)", lines)

    def custom_file_practice(self):
        self.print_header("사용자 파일 불러오기")
        files = [f for f in os.listdir('.') if f.endswith('.txt')]
        
        if not files:
            print("\n[알림] 폴더에 '.txt' 파일이 없습니다.")
            input("Enter를 눌러 돌아갑니다...")
            return

        print("\n[ 파일 목록 ]")
        for idx, filename in enumerate(files):
            print(f"{idx + 1}. {filename}")
        
        try:
            selection = int(input("\n파일 번호 선택: ")) - 1
            if 0 <= selection < len(files):
                filename = files[selection]
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                except UnicodeDecodeError:
                    with open(filename, 'r', encoding='cp949') as f:
                        lines = f.readlines()
                self.run_text_practice(f"파일 연습: {filename}", lines)
            else:
                play_sound('wrong')
                print("잘못된 번호입니다.")
                time.sleep(1)
        except ValueError:
            play_sound('wrong')
            print("숫자를 입력하세요.")
            time.sleep(1)

    def venetia_game(self):
        score = 0
        game_duration = 40
        start_game_time = time.time()
        
        while True:
            remain_time = int(game_duration - (time.time() - start_game_time))
            if remain_time <= 0: break
                
            self.print_header("베네치아 게임")
            print(f"남은 시간: {remain_time}초 | 현재 점수: {score}점")
            
            target_word = random.choice(GAME_WORDS)
            print(f"\n ▼ ▼ ▼ [[ {target_word} ]] ▼ ▼ ▼\n")
            
            user_input = input("단어 입력: ")
            if int(game_duration - (time.time() - start_game_time)) <= 0: break
            
            if user_input == target_word:
                score += 100
                play_sound('correct') # 딩동!
                print("Nice! (+100점)")
            else:
                play_sound('wrong') # 띡!
                print("Miss!")
            time.sleep(0.3)
        
        self.print_header("GAME OVER")
        print(f"\n최종 점수: {score}점")
        if score > self.records['game_best']:
            play_sound('high_score') # 빠라바밤!
            self.records['game_best'] = score
            save_records(self.records)
            print("★ 최고 점수 갱신! ★")
        else:
            play_sound('wrong') # 게임 오버 소리
            
        input("\n엔터 키를 누르면 복귀합니다...")

    def main_menu(self):
        while True:
            self.print_header("메인 메뉴")
            print("\n1. 단문 연습 (명언)")
            print("2. 장문 연습 (기본 문학)")
            print("3. 사용자 텍스트 불러오기 (.txt)")
            print("4. 베네치아 게임 (산성비)")
            print("5. 기록 초기화")
            print("0. 종료")
            print("-" * 50)
            
            choice = input("선택 >> ")
            
            if choice == '1': self.short_practice()
            elif choice == '2': self.long_practice()
            elif choice == '3': self.custom_file_practice()
            elif choice == '4': self.venetia_game()
            elif choice == '5':
                if input("기록 삭제 (y/n)? ").lower() == 'y':
                    self.records = {"short_best": 0, "game_best": 0, "total_typed": 0}
                    save_records(self.records)
                    print("초기화 완료.")
                    time.sleep(1)
            elif choice == '0': break
            else:
                play_sound('wrong')

if __name__ == "__main__":
    app = HanmeTyping()
    app.main_menu()

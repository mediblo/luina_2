# Luina 2

Discord.py 기반 멀티 게임/유틸 디스코드 봇입니다.

- 일반 유틸 명령어
- 외부 API 명령어
- League of Legends 명령어
- Lost Ark 명령어
- MapleStory 명령어

## 들어가기에 앞서
> 작성된 모든 API 키는 Public에 맞춰 전부 폐기 및 재할당을 받아 사용이 불가능합니다.  
> 또한 대부분의 임베드 꾸미기는 미술적 감각이 없는 개발자를 Gemini가 도와줬습니다.

## 기술 스택

- Python 3.14.6 (`.python-version`)
- discord.py[voice] 2.7.1
- httpx 0.28.1
- lyricsgenius 3.12.2
- aiolimiter 1.2.1
- firebase-admin 7.1.0
- python-dotenv 1.0.1

## 디렉터리 구조

```text
.
├─ main.py
├─ requirements.txt
├─ Procfile
├─ .python-version
├─ TODO.txt
├─ notice.txt
├─ character_sheet.md        # 🎭 루이나 캐릭터 설정 시트
├─ how_to_use.md            # 🌙 루이나 컨셉 반영 사용 설명서
│
├─ config/
│  └─ settings.py
│
├─ cogs/
│  ├─ general.py
│  ├─ api.py
│  ├─ riot.py
│  ├─ lostark.py
│  ├─ maplestory.py
│  └─ help.py
│
├─ utils/
│  ├─ embed_builder.py
│  ├─ http_client.py
│  └─ logger.py              # 봇 내부 로그 기록
│
├─ services/
│  ├─ __init__.py
│  ├─ firebase.py            # Firebase 공통 함수 (로그 및 메이플 데이터 처리)
│  └─ log_service.py         # 로그 저장/삭제/Flush
│
├─ data/
│  └─ kkuko_db.txt           # 끄투 코리아 단어 DB
│
├─ Luina/                    # 🖼️ 봇 프로필 이미지 및 캐릭터 시트 이미지 리소스
│
└─ history.txt               # 봇 개발 이력
```

## 실행 준비

1. Python 3.14.6 환경 준비
2. 패키지 설치

```bash
pip install -r requirements.txt
```

3. 환경변수 설정

`config/settings.py`에서 아래 키를 `os.getenv(...)`로 읽습니다.

- `BOT_TOKEN`
- `OPENWEATHERMAP_API`
- `EXCHANGERATE_API`
- `GENIUS_API`
- `LOSTARK_API`
- `MAPLESTORY_API`
- `ON_WORD_API`
- `RIOT_API`
- `FIREBASE_CREDENTIALS`
- `FIREBASE_URL`

예시 (PowerShell):

```powershell
$env:BOT_TOKEN="..."
$env:OPENWEATHERMAP_API="..."
$env:EXCHANGERATE_API="..."
$env:GENIUS_API="..."
$env:LOSTARK_API="..."
$env:MAPLESTORY_API="..."
$env:ON_WORD_API="..."
$env:RIOT_API="..."
$env:FIREBASE_CREDENTIALS="..."
$env:FIREBASE_URL="..."
```

## 실행

로컬 실행:

```bash
python main.py
```

Procfile 기반 실행:

```text
worker: python main.py
```

## 동작 방식

- `main.py`에서 `cogs/`의 모든 파이썬 파일을 자동 로드합니다.
- 슬래시 명령어는 `self.tree.sync()`로 전역 동기화합니다.
- `on_message`에서 특정 채널에 대해 다음 자동 처리를 수행합니다.
	- 커스텀 이모지 메시지 확대 임베드 전송
	- Base64 문자열 디코딩 응답

## 명령어 목록

### 일반 (`cogs/general.py`)

- `/정보`
- `/핑`
- `/계산기`
- `/시간`
- `/가위바위보`
- `/소라고동`
- `/선택`
- `/b64`
- `/청소`
- `/초대`

### API (`cogs/api.py`)

- `/날씨`
- `/환율`
- `/사전`
- `/가사`

### League of Legends (`cogs/riot.py`)

- `/전적`
- `/롤`
- `/롤챔프`
- `/스킬가속`

추가 기능:

- `/롤챔프` 결과에 버튼 UI(상세 정보) 제공

### Lost Ark (`cogs/lostark.py`)

- `/로아_공지`
- `/로아_이벤트`
- `/로아_캐릭터`

추가 기능:

- `/로아_캐릭터` 결과에 버튼 UI(스킬/수집) 제공

### MapleStory (`cogs/maplestory.py`)

- `/메이플_등록`
- `/메이플_삭제`
- `/메이플_랭킹`
- `/메이플_캐릭터`
- `/메이플_공지`
- `/메이플_이벤트`

주의:

- 등록 데이터는 `Firebase`에 저장됩니다.

### 도움말 (`cogs/help.py`)

- `/도움말`
- `/도움말 명령어:<이름>`

## 데이터 파일

- `data/kkuko_db.txt`
	- 대용량 단어 사전 파일 (약 332,534 라인)
	- 텍스트 기반 사전 데이터
	- 끄투 코리아 DB

## 운영 메모

- 시작 시 각 코그에서 API 상태 체크 로그를 출력합니다.
- 오류 발생 시 앱 커맨드 에러 핸들러에서 개발자 DM 전송을 시도합니다.
- 개발 이력은 `history.txt`에 기록되어 있습니다.
- 몇몇 코드들은 서버 및 유저에 한하여 하드코딩 되어 있습니다.
- 가져도 딱히 상관은 없는 guild_id와 member_id입니다.
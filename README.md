# MoodNote

일기와 음성 기록을 기반으로 감정을 분석하고, AI가 맞춤 상담 피드백을 제공하는 감성 저널링 앱
An AI-powered emotional journaling app that analyzes diary and voice entries, then provides personalized counseling feedback.

---

## 한국어

### 프로젝트 개요

- 개발 기간: 2026.09 ~ (진행 중)
- 2026-2학기 지능형시스템프로젝트 졸업작품
- 일기를 쓰면 AI가 내용을 분석해 무드 그래프로 시각화하고, 감정 상태에 맞춘 AI 상담 피드백을 제공하는 소프트웨어와, 포켓형 E-ink 단말기로 음성을 녹음하면 자동으로 전사되어 일기로 등록되는 보이스노트 하드웨어를 통합적으로 구축하는 IoT 융합 프로젝트입니다.
- 소프트웨어 융합: 감정 좌표 기반 데이터베이스 설계, LLM 기반 감정분석, RAG 기반 AI 상담 챗봇
- 하드웨어 융합: EasyEDA 기반 커스텀 PCB 설계, Fusion 360 정밀 기구 설계, ESP32-S3 초저전력 음성 수음, Wi-Fi 오디오 업로드

### 팀 구성 및 담당 역할

| 담당 | 역할 |
|---|---|
| 유정 (SW / 기획) | 데이터베이스 설계, 감정분석 로직 설계, AI 상담 프롬프트 설계, 프로젝트 기획 |
| SW 구현 담당 | 백엔드 API 구현, RAG 파이프라인 구현 |
| HW 담당 | 시스템 회로도 설계, EasyEDA 기반 커스텀 PCB 아트워크 및 SMT 발주, Fusion 360 기구 하우징 모델링, 3D 프린팅 공차 조립, ESP32 임베디드 펌웨어 개발 |

### 기술 스택

**Backend & AI**
- Python (FastAPI 예정), SQLite/PostgreSQL
- 학교 AI서버 오픈소스 LLM, RAG (Retrieval-Augmented Generation)
- Whisper STT

**Circuit & PCB**
- EasyEDA, JLCPCB SMT
- Li-Po Charging Circuit (TP4056), LDO Power Tree

**3D Design & CAD**
- Fusion 360, SLA/FDM 3D Printing
- DFM (Design for Manufacturing)

**Embedded Hardware**
- ESP32-S3
- I2S Digital Mic (INMP441)
- SPI E-ink Display (1.54"/2.13")

**Firmware & Cloud SW**
- C/C++ (ESP-IDF / Arduino)
- Python (FastAPI), Whisper STT, LLM API

### 핵심 구현 및 특징

**1. 감정 좌표 기반 데이터베이스 설계**
무드미터(Mood Meter) 이론에 기반해 감정을 에너지 축과 유쾌함 축의 2차원 좌표로 정량화. 사용자가 100개 감정 단어 중 하나를 선택하면 고정된 좌표값을 즉시 부여받는 구조로, AI가 임의로 숫자를 추측하지 않도록 설계.

**2. 개인화된 AI 상담 (RAG 기반)**
사용자 프로필, 인간관계, 과거 일기 기록, 상담 기법 지식베이스를 검색해 참고자료로 활용한 뒤 응답을 생성. 대화가 누적될수록 사용자에 대한 이해를 갱신하는 자기모델(Self-Model) 구조를 포함.

**3. 사용자 반응 기반 피드백 검증**
AI 상담 피드백에 대해 사용자가 직접 도움이 되었는지 여부를 기록. AI의 자체 평가가 아닌 실제 사용자 판단을 기반으로 데이터가 축적되는 구조.

**4. 원보드 커스텀 PCB 및 정밀 기구 설계 (하드웨어)**
ESP32-S3 메인 컨트롤러 주변으로 Type-C 충전 회로(TP4056), 저낙차 LDO 레귤레이터, I2S 디지털 마이크, E-ink 승압 구동 회로를 단일 기판(EasyEDA)에 집약. 디지털 버스 라인과 아날로그/파워 그라운드 플레인을 분리 배선해 오디오 신호 왜곡과 노이즈 유입을 차단. Fusion 360으로 설계한 포켓형 하우징은 PCB 3D STEP 파일과 1:1 정합해 커넥터 타공부·택트 스위치 간 ±0.15mm 정밀 공차를 적용하고, Li-Po 배터리 안착 슬롯과 E-ink 보호 베젤을 일체화 성형. E-ink 특성을 활용해 화면 갱신 직후 전원을 차단하는 파워 게이팅과 딥슬립·외부 인터럽트 기상 구조로 비작동시 소비전류를 수십 µA 수준으로 억제.

**5. 음성 일기 자동 등록 (하드웨어-소프트웨어 통합)**
I2S 마이크로 수음한 오디오를 DMA 기반 실시간 링버퍼에 기록해 CPU 부하 없이 처리하고, 녹음 종료 즉시 Wi-Fi로 청크 분할 전송. 백엔드에서 침묵 구간을 필터링한 뒤 Whisper로 전사하고, 텍스트 일기와 동일한 감정분석 파이프라인을 거쳐 DIARY_ENTRIES에 자동 등록.

### 개발 단계

| 단계 | 소프트웨어 | 하드웨어 |
|---|---|---|
| 1. 기획 및 사양 정의 | 스코프 확정(SW+HW 트랙), 팀 역할분담 | 배터리 런타임 목표(1회 충전 7일 이상), 포켓 폼팩터 규격 산출, MCU/I2S 마이크/E-ink 핀맵 정의 |
| 2. 설계 | 데이터베이스 스키마 설계 | 상용 ESP32 개발보드 기반 1차 PoC — 브레드보드 검증, 마이크 수음→Wi-Fi 전송→E-ink 렌더링 엔드투엔드 파이프라인 검증 |
| 3. 로직/회로 설계 | 감정분석 및 RAG 상담 로직 설계 | EasyEDA 회로도 작성 및 2레이어 PCB 아트워크·Gerber 발주, Fusion 360 하우징 모델링 및 1차 3D 프린팅 시제품 |
| 4. 구현 및 통합 | 백엔드 API, RAG 파이프라인 구현, 통합 테스트 | 커스텀 PCB SMT/솔더링, 하우징 공차 보정, 배터리 구동시간·Wi-Fi 연결 안정성 튜닝 |

### 현재 상태

| 항목 | 상태 |
|---|---|
| 스코프 및 역할 분담 | 완료 |
| 데이터베이스 스키마 설계 | 완료 |
| 감정분석 로직 설계 | 진행중 |
| 백엔드 API 구현 | 예정 |
| 하드웨어 PoC (개발보드 검증) | 예정 |
| EasyEDA 회로/PCB 설계 | 예정 |
| RAG 챗봇 구현 | 예정 |
| 통합 테스트 | 예정 |

### 관련 문서

- `/docs` 폴더: 프로젝트 현황 문서, 데이터베이스 스키마, 아키텍처 다이어그램

---

## English

### Overview

- Development period: September 2026 - present
- Capstone project for the Intelligent Systems Project course, Fall 2026
- MoodNote combines a diary-based software system that analyzes emotional states and provides AI counseling feedback with a companion voice-note hardware device: a pocket-sized E-ink terminal that automatically transcribes recordings into diary entries.
- Software integration: emotion-coordinate database design, LLM-based emotion analysis, RAG-based AI counseling chatbot
- Hardware integration: EasyEDA-based custom PCB design, Fusion 360 precision mechanical design, ESP32-S3 ultra-low-power voice capture, Wi-Fi audio upload

### Team and Roles

| Member | Role |
|---|---|
| Yu Jung (SW / Planning) | Database design, emotion analysis logic design, AI counseling prompt design, project planning |
| SW Implementation | Backend API implementation, RAG pipeline implementation |
| HW Implementation | System circuit schematic design, custom PCB artwork and SMT ordering via EasyEDA, Fusion 360 housing modeling, 3D-printed tolerance assembly, ESP32 firmware development |

### Tech Stack

**Backend & AI**
- Python (FastAPI planned), SQLite/PostgreSQL
- University AI server open-source LLM, RAG (Retrieval-Augmented Generation)
- Whisper STT

**Circuit & PCB**
- EasyEDA, JLCPCB SMT
- Li-Po Charging Circuit (TP4056), LDO Power Tree

**3D Design & CAD**
- Fusion 360, SLA/FDM 3D Printing
- DFM (Design for Manufacturing)

**Embedded Hardware**
- ESP32-S3
- I2S Digital Mic (INMP441)
- SPI E-ink Display (1.54"/2.13")

**Firmware & Cloud SW**
- C/C++ (ESP-IDF / Arduino)
- Python (FastAPI), Whisper STT, LLM API

### Core Features

**1. Emotion-Coordinate Database Design**
Based on the Mood Meter framework, emotions are quantified on two axes: energy and pleasantness. Users select one of 100 predefined emotion words, each mapped to fixed coordinates, so the system never relies on an LLM guessing a numeric score.

**2. Personalized AI Counseling (RAG-based)**
Responses are generated using retrieved context from the user's profile, relationships, past diary entries, and a counseling-technique knowledge base. Includes a Self-Model structure that is updated as conversations accumulate, refining the system's understanding of the user over time.

**3. Feedback Validated by User Reaction**
Users mark whether each AI counseling response was actually helpful. Data accumulates based on real user judgment rather than the AI's self-assessment.

**4. One-Board Custom PCB and Precision Mechanical Design (Hardware)**
Integrates the ESP32-S3 main controller, Type-C charging circuit (TP4056), a low-dropout LDO regulator, an I2S digital microphone, and an E-ink boost driver circuit onto a single EasyEDA-designed board, with digital bus lines routed separately from analog/power ground planes to prevent audio signal distortion and noise. The Fusion 360-designed pocket housing is matched 1:1 against the PCB's 3D STEP file, applying +/-0.15mm interference/clearance tolerances at connector cutouts and tact switches, with an integrated Li-Po battery slot and E-ink protective bezel. Power gating cuts main power immediately after each E-ink refresh, and a deep-sleep sequence with hardware interrupt wake keeps idle current draw in the tens of microamps.

**5. Automatic Voice Diary Registration (Hardware-Software Integration)**
Audio captured via the I2S microphone is buffered in a real-time ring buffer using DMA, avoiding CPU load, then transmitted to the backend in chunks over Wi-Fi immediately after recording ends. The backend filters silent segments, transcribes the audio with Whisper, and passes it through the same emotion analysis pipeline as text diary entries, registering it automatically in DIARY_ENTRIES.

### Development Phases

| Phase | Software | Hardware |
|---|---|---|
| 1. Planning and Spec Definition | Defined SW+HW scope and team roles | Set battery runtime target (7+ days per charge) and pocket form factor spec; finalized MCU/I2S mic/E-ink pinmap |
| 2. Design | Designed database schema | First PoC on a commercial ESP32 dev board - breadboard verification, end-to-end mic capture -> Wi-Fi transfer -> E-ink rendering pipeline |
| 3. Logic / Circuit Design | Designed emotion analysis and RAG counseling logic | EasyEDA schematic and 2-layer PCB artwork, Gerber files ordered; Fusion 360 housing modeling and first 3D-printed prototype |
| 4. Implementation and Integration | Backend API, RAG pipeline implementation, integration testing | Custom PCB SMT/soldering, housing tolerance correction, battery runtime and Wi-Fi stability tuning |

### Current Status

| Item | Status |
|---|---|
| Scope and role assignment | Done |
| Database schema design | Done |
| Emotion analysis logic design | In progress |
| Backend API implementation | Planned |
| Hardware PoC (dev board verification) | Planned |
| EasyEDA circuit/PCB design | Planned |
| RAG chatbot implementation | Planned |
| Integration testing | Planned |

### Related Documents

- `/docs` folder: project status document, database schema, architecture diagrams

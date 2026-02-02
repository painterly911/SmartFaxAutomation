#  AI 기반 스마트 팩스 자재 관리 시스템 (Smart Fax Automation System)

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?logo=streamlit&logoColor=white)
![Google Cloud](https://img.shields.io/badge/Google_Cloud_Vision-OCR-4285F4?logo=google-cloud&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?logo=sqlite&logoColor=white)

> **수기 팩스 주문서를 3초 만에 엑셀 데이터로 변환하는 업무 자동화 솔루션**

## 📸 실행 화면 (Screenshots)

| 메인 대시보드 및 조회 | 팩스 인식 결과 | 
| :---: | :---: |
| <img width="2560" height="1392" alt="스크린샷 2026-02-02 210018" src="https://github.com/user-attachments/assets/60aa6288-cdf0-4e55-932a-528f933ec267" />| <img width="2560" height="1392" alt="스크린샷 2026-02-02 212619" src="https://github.com/user-attachments/assets/be09c452-31e8-4817-9d47-0a2115b843f6" />|
| **누적 내역 조회 화면** | **OCR 인식 및 파싱 결과** |
|<img width="2560" height="1392" alt="스크린샷 2026-02-02 212645" src="https://github.com/user-attachments/assets/71bf7ad0-d33b-4c3b-b647-149c5c320bbe" />|<img width="2560" height="1392" alt="스크린샷 2026-02-02 213028" src="https://github.com/user-attachments/assets/585563c5-239d-40f7-9d94-ea467cdc639f" />|
<br>

## 프로젝트 개요 (Overview)
현장이나 거래처에서 들어오는 **수기/인쇄 팩스 주문서**를 수동으로 엑셀에 입력하는 비효율적인 업무를 개선하기 위해 개발했습니다. 

**Google Cloud Vision API**의 강력한 **OCR(광학 문자 인식)** 기술과 Python의 데이터 처리 라이브러리를 결합하여, 이미지 속의 날짜, 현장명, 품목, 수량을 자동으로 추출하고 DB에 적재합니다. 단순한 텍스트 추출을 넘어, 오타 자동 보정(Fuzzy Matching)과 **현장명 정규화**를 통해 데이터의 정확도를 높이고 사용자의 개입을 최소화했습니다.

<br>

##  핵심 기능 (Key Features)

### 1. 고성능 OCR 및 파싱
* **Google Cloud Vision API**를 연동하여 저화질 팩스에서도 높은 인식률 확보.
* 정규표현식(Regex)을 활용해 `날짜`, `현장명`, `품목`, `수량`을 정교하게 분리.
* **Multi-page 지원:** TIFF 등 여러 장으로 된 팩스 문서도 한 번에 일괄 처리.

### 2. 데이터 전처리 및 정규화 (Data Cleaning)
* **노이즈 필터링:** 팩스 상단의 전송 시간(`13:33`), 페이지 번호(`001/001`) 등이 품목으로 오인식되는 것을 방지.
* **현장명 통일:** `현장A(1공구)`와 `현장A (1공구)` 등 띄어쓰기 차이로 데이터가 분산되는 문제를 해결하기 위한 자동 포맷팅 기능 구현.

### 3. 지능형 오타 보정 (Smart Correction)
* `TheFuzz` 라이브러리를 활용하여 **품목 마스터 DB**와 OCR 결과의 유사도를 분석.
* 단순 오타(예: `창랩` → `청랩`)는 자동으로 수정하되, **상세 규격(예: `5*6`)이 포함된 경우 원본을 유지**하는 로직 적용.

### 4. 사용자 친화적 기능 (UI/UX)
* **Streamlit** 기반의 직관적인 웹 인터페이스 제공.
* **Excel 다운로드 커스텀:** 현장명을 파일명으로 자동 지정하거나, 사용자가 직접 수정하여 다운로드 가능.
* **SQLite DB 연동:** 모든 데이터를 로컬 DB에 영구 저장 및 누적 관리.

<br>

##  기술 스택 (Tech Stack)

| 구분 | 기술 | 설명 |
| :--- | :--- | :--- |
| **Language** | **Python** | 전체 로직 구현 |
| **Framework** | **Streamlit** | 웹 기반 UI/UX 구축 |
| **AI / OCR** | **Google Cloud Vision API** | 이미지 텍스트 추출 |
| **Data Processing** | **Pandas, TheFuzz** | 데이터 정제 및 유사도 분석 |
| **Database** | **SQLite** | 경량 로컬 데이터베이스 |
| **Deploy** | **WinPython** | 무설치(Portable) 배포 환경 |

<br>

##  문제 해결 과정 (Troubleshooting)

개발 과정에서 발생한 주요 이슈와 해결 방법입니다.

### 1. 헤더/푸터 노이즈 데이터 혼입 문제
* **문제:** 팩스 전송 시간인 `13:33`이 OCR 과정에서 `품명: 3`, `수량: 33`인 품목 데이터로 잘못 인식됨.
* **해결:** 행(Line) 단위 분석 시 `FAX`, `페이지`, `전송` 등의 키워드가 포함되거나, `날짜 패턴(202x년)`과 `시간 패턴(:)`이 동시에 존재하는 줄을 강제로 무시하는 필터링 로직 추가.

### 2. 오타 보정 시 규격 정보 유실 문제
* **문제:** `방염천막(5*6)`이 DB상의 `방염천막`과 유사하다는 이유로, 뒤의 규격 정보(`5*6`)가 삭제되고 단순화되는 문제.
* **해결:** 유사도가 높더라도 **OCR 결과물의 글자 수가 마스터 데이터보다 현저히 긴 경우(3글자 이상)**, 상세 규격이 포함된 것으로 간주하여 보정을 건너뛰는 예외 처리 로직 구현.

### 3. 현장명 데이터 파편화 문제
* **문제:** 같은 현장임에도 `(2607)`과 `( 2607 )`처럼 괄호 띄어쓰기에 따라 다른 현장으로 분류됨.
* **해결:** `clean_site_name` 함수를 도입하여 저장 직전 괄호 앞뒤의 공백 규칙을 강제로 통일(Normalization)시킴.


<br>

## 배포 및 실행 가이드 (Deployment & Execution)

이 프로젝트는 Python이 설치된 개발 환경과 Python이 없는 일반 사무용 PC 모두에서 실행 가능하도록 설계되었습니다.

## 무설치 포터블 환경 (Portable Environment)
Python을 설치할 수 없거나 인터넷 보안이 강화된 현장/사무실 PC를 위한 배포 방식입니다. USB에 담아 이동할 수 있습니다

```bash
📦 MyFaxApp (배포 폴더)
 ┣ 📂 python  # [내장] 파이썬 엔진 (수정 금지)
 ┣ 📜 app.py               # 소스 코드
 ┣ 📜 my-key.json          # Google Vision API 키
 ┣ 📜 master_items.xlsx    # 품목 마스터 엑셀
 ┣ 📜 fax_db.sqlite        # DB 파일 (여기에 데이터가 쌓입니다)
 ┗ 🚀 SmartFaxAutomation.bat          # [실행] 사용자는 이것만 클릭하면 됩니다
 ```

전달받은 압축 파일(ZIP)을 바탕화면 등에 풉니다.

## 폴더 내의 🚀 SmartFaxAutomation.bat 파일을 더블 클릭합니다.

**Google Vision API 키, 품목 마스터 엑셀은 추가하셔야 작동합니다.** 

검은색 실행 창(Console)이 뜨고 잠시 후 웹 브라우저가 자동으로 열리며 프로그램이 시작됩니다.
(주의: 검은색 창을 끄면 프로그램이 종료됩니다.)

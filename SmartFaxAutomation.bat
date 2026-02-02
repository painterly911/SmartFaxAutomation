@echo off
:: 한글 깨짐 방지 (UTF-8 설정)
@chcp 65001 > nul

cd /d "%~dp0"

set PYTHON_FOLDER=python
:: 파이썬이 진짜 있는지 확인하는 안전장치
if not exist "%PYTHON_FOLDER%\python.exe" (
    echo.
    echo [오류] 파이썬 폴더를 찾을 수 없습니다!
    echo 현재 설정된 이름: %PYTHON_FOLDER%
    echo.
    echo 1. 폴더 안에 'python-...'으로 시작하는 폴더가 있는지 확인하세요.
    echo 2. 그 이름을 복사해서 이 bat 파일의 'set PYTHON_FOLDER=...' 부분에 붙여넣으세요.
    echo.
    pause
    exit
)

echo.
echo  팩스 프로그램을 실행합니다... (창을 닫지 마세요)
echo.

:: 프로그램 실행 명령어
"%PYTHON_FOLDER%\python.exe" -m streamlit run app.py --server.headless true --browser.gatherUsageStats false

pause
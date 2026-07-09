@echo off

if not exist ".env" (
    echo [ERROR] .env not found. Copy .env.example to .env and fill in your API keys.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\activate" (
    echo [INFO] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment. Make sure Python is installed.
        pause
        exit /b 1
    )
)

call .venv\Scripts\activate

pip install -r requirements.txt -q

echo [INFO] Starting server...
start "BabelDOC" python app.py

timeout /t 2 /nobreak >nul

echo [INFO] Opening browser...
start http://127.0.0.1:7860

echo [INFO] Done. Close the server window to stop.

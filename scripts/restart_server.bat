@echo off
echo 正在停止所有 Python 进程...
taskkill /F /IM python.exe 2>nul
timeout /t 2 /nobreak >nul

echo 清理 __pycache__...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"

echo 启动服务器...
python main.py

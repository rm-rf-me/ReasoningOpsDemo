@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM 评测结果展示系统 - Windows 启动脚本

set PORT=%PORT%
if "%PORT%"=="" set PORT=5000

echo.
echo =================================
echo 🚀 启动评测结果展示系统
echo =================================
echo.

REM 检查Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    where python3 >nul 2>&1
    if %errorlevel% neq 0 (
        echo ❌ 未找到Python，请确保Python 3.8+已安装
        pause
        exit /b 1
    )
    set PYTHON_CMD=python3
) else (
    set PYTHON_CMD=python
)

REM 检查Python版本
for /f "tokens=2" %%i in ('%PYTHON_CMD% --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Python版本: %PYTHON_VERSION%

REM 检查虚拟环境
if exist "venv\Scripts\python.exe" (
    echo ✅ 检测到venv环境
    set PYTHON_CMD=venv\Scripts\python.exe
    set ENV_TYPE=venv
) else if exist "venv\bin\python.exe" (
    echo ✅ 检测到venv环境
    set PYTHON_CMD=venv\bin\python.exe
    set ENV_TYPE=venv
) else (
    echo ⚠️  未检测到虚拟环境，使用系统Python
    set ENV_TYPE=system
)

REM 检查依赖
echo.
echo 📦 检查Python依赖...
%PYTHON_CMD% -c "import flask" >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  Flask未安装，正在安装依赖...
    %PYTHON_CMD% -m pip install --upgrade pip -q
    %PYTHON_CMD% -m pip install -r requirements.txt -q
    if %errorlevel% neq 0 (
        echo ❌ Python依赖安装失败
        pause
        exit /b 1
    )
    echo ✅ Python依赖安装完成
) else (
    echo ✅ Python依赖已就绪
)

REM 检查pandas
%PYTHON_CMD% -c "import pandas" >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  pandas未安装，Excel读取功能将不可用
    echo 💡 如需使用Excel功能，请运行: pip install pandas openpyxl
)

REM 检查端口
echo.
echo 🔍 检查端口 %PORT% 是否可用...
netstat -an | findstr ":%PORT%.*LISTENING" >nul 2>&1
if %errorlevel% equ 0 (
    echo ❌ 端口 %PORT% 已被占用
    echo 💡 请使用其他端口: set PORT=8000 && start.bat
    pause
    exit /b 1
)
echo ✅ 端口 %PORT% 可用

REM 检查前端
echo.
echo 🎨 检查前端构建...
if exist "frontend\dist" (
    echo ✅ 前端已构建
) else (
    echo ⚠️  前端未构建，检查Node.js...
    where node >nul 2>&1
    if %errorlevel% neq 0 (
        echo ❌ 未找到Node.js，无法构建前端
        echo 💡 请安装Node.js 16+，或使用已包含dist目录的版本
        pause
        exit /b 1
    )
    
    echo ✅ 检测到Node.js
    if not exist "frontend\node_modules" (
        echo 📦 安装前端依赖...
        cd frontend
        call npm install --no-fund --no-audit
        if !errorlevel! neq 0 (
            echo ❌ 前端依赖安装失败
            cd ..
            pause
            exit /b 1
        )
        cd ..
    )
    
    echo 🔨 构建前端应用...
    cd frontend
    call npm run build
    if !errorlevel! neq 0 (
        echo ❌ 前端构建失败
        cd ..
        pause
        exit /b 1
    )
    cd ..
    echo ✅ 前端构建成功
)

REM 启动服务
echo.
echo 🌐 启动Flask服务 (端口 %PORT%)...
set PORT=%PORT%
start /b %PYTHON_CMD% app.py
timeout /t 3 /nobreak >nul

REM 检查服务是否启动
curl -s http://localhost:%PORT%/api/stats/overview >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 后端服务启动失败或无法访问
    echo 💡 请检查Flask日志输出
    pause
    exit /b 1
)

echo.
echo =================================
echo 🎉 服务启动完成
echo =================================
echo.
echo 🌐 完整应用: http://localhost:%PORT%
echo 🔌 Flask API: http://localhost:%PORT%/api/
echo.
echo 按 Ctrl+C 停止服务
echo =================================
echo.

REM 等待用户中断
pause


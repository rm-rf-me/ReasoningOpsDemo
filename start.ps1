# 评测结果展示系统 - Windows PowerShell 启动脚本

$ErrorActionPreference = "Stop"

# 设置编码
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 配置参数
$PORT = if ($env:PORT) { $env:PORT } else { 5000 }
$REBUILD_FRONTEND = if ($env:REBUILD_FRONTEND -eq "true") { $true } else { $false }

function Print-Info {
    Write-Host "ℹ️  $args" -ForegroundColor Blue
}

function Print-Success {
    Write-Host "✅ $args" -ForegroundColor Green
}

function Print-Warning {
    Write-Host "⚠️  $args" -ForegroundColor Yellow
}

function Print-Error {
    Write-Host "❌ $args" -ForegroundColor Red
}

function Print-Header {
    Write-Host ""
    Write-Host "=================================" -ForegroundColor Blue
    Write-Host "$args" -ForegroundColor Blue
    Write-Host "=================================" -ForegroundColor Blue
    Write-Host ""
}

Print-Header "🚀 启动评测结果展示系统"

Print-Info "服务端口: $PORT"

# 检查Python
$pythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $pythonCmd = "python3"
} else {
    Print-Error "未找到Python，请确保Python 3.8+已安装"
    exit 1
}

# 获取Python版本
$pythonVersion = & $pythonCmd --version 2>&1 | Select-Object -First 1
Print-Success "Python版本: $pythonVersion"

# 检查虚拟环境
$envType = "system"
if (Test-Path "venv\Scripts\python.exe") {
    $pythonCmd = "venv\Scripts\python.exe"
    $envType = "venv"
    Print-Success "检测到venv环境"
} elseif (Test-Path "venv\bin\python.exe") {
    $pythonCmd = "venv\bin\python.exe"
    $envType = "venv"
    Print-Success "检测到venv环境"
} else {
    Print-Warning "未检测到虚拟环境，使用系统Python"
}

# 检查依赖
Print-Info "检查Python依赖..."
$hasFlask = & $pythonCmd -c "import flask" 2>&1
if ($LASTEXITCODE -ne 0) {
    Print-Warning "Flask未安装，正在安装依赖..."
    & $pythonCmd -m pip install --upgrade pip -q
    & $pythonCmd -m pip install -r requirements.txt -q
    if ($LASTEXITCODE -ne 0) {
        Print-Error "Python依赖安装失败"
        exit 1
    }
    Print-Success "Python依赖安装完成"
} else {
    Print-Success "Python依赖已就绪"
}

# 检查pandas
$hasPandas = & $pythonCmd -c "import pandas" 2>&1
if ($LASTEXITCODE -ne 0) {
    Print-Warning "pandas未安装，Excel读取功能将不可用"
    Print-Info "如需使用Excel功能，请运行: pip install pandas openpyxl"
}

# 检查端口
Print-Info "检查端口 $PORT 是否可用..."
$portInUse = Get-NetTCPConnection -LocalPort $PORT -ErrorAction SilentlyContinue
if ($portInUse) {
    Print-Error "端口 $PORT 已被占用"
    Print-Info "请使用其他端口: `$env:PORT=8000; .\start.ps1"
    exit 1
}
Print-Success "端口 $PORT 可用"

# 检查前端
Print-Info "检查前端构建..."
if (Test-Path "frontend\dist") {
    if ($REBUILD_FRONTEND) {
        Print-Info "强制重新构建前端..."
        Remove-Item -Recurse -Force "frontend\dist"
    } else {
        Print-Success "前端已构建"
    }
}

if (-not (Test-Path "frontend\dist") -or $REBUILD_FRONTEND) {
    Print-Info "需要构建前端，检查Node.js环境..."
    
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
        Print-Error "未找到Node.js，无法构建前端"
        Print-Info "请安装Node.js 16+，或使用已包含dist目录的版本"
        exit 1
    }
    
    $nodeVersion = node --version
    Print-Success "Node.js版本: $nodeVersion"
    
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        Print-Error "未找到npm，请确保npm已安装"
        exit 1
    }
    
    Print-Success "npm版本: $(npm --version)"
    
    if (-not (Test-Path "frontend\node_modules")) {
        Print-Info "安装前端依赖..."
        Set-Location frontend
        npm install --no-fund --no-audit
        if ($LASTEXITCODE -ne 0) {
            Print-Error "前端依赖安装失败"
            Set-Location ..
            exit 1
        }
        Set-Location ..
        Print-Success "前端依赖安装完成"
    }
    
    Print-Info "构建前端应用（这可能需要几分钟）..."
    Set-Location frontend
    npm run build
    if ($LASTEXITCODE -ne 0) {
        Print-Error "前端构建失败"
        Set-Location ..
        exit 1
    }
    Set-Location ..
    Print-Success "前端构建成功"
}

# 启动服务
Print-Info "启动Flask服务 (端口 $PORT)..."
$env:PORT = $PORT
$backendProcess = Start-Process -FilePath $pythonCmd -ArgumentList "app.py" -PassThru -NoNewWindow

Start-Sleep -Seconds 3

# 检查服务是否启动
try {
    $response = Invoke-WebRequest -Uri "http://localhost:$PORT/api/stats/overview" -TimeoutSec 2 -ErrorAction SilentlyContinue
    Print-Success "Flask服务已启动"
} catch {
    Print-Error "后端服务启动失败或无法访问"
    Print-Info "请检查Flask日志输出"
    Stop-Process -Id $backendProcess.Id -ErrorAction SilentlyContinue
    exit 1
}

Print-Header "🎉 服务启动完成"
Write-Host "🌐 完整应用: http://localhost:$PORT" -ForegroundColor Green
Write-Host "🔌 Flask API: http://localhost:$PORT/api/" -ForegroundColor Green
Write-Host ""
Print-Info "按 Ctrl+C 停止服务"
Write-Host ""

# 等待用户中断
try {
    Wait-Process -Id $backendProcess.Id
} catch {
    Stop-Process -Id $backendProcess.Id -ErrorAction SilentlyContinue
    Print-Info "服务已停止"
}


#!/bin/bash

# 评测结果展示系统 - 一键启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo ""
    echo -e "${BLUE}=================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=================================${NC}"
    echo ""
}

# 显示使用说明
show_help() {
    print_header "📖 使用说明"
    echo "  ./start.sh                    # 交互式启动（推荐新手）"
    echo "  ./start.sh --auto             # 自动检测并使用已有环境"
    echo "  PORT=8000 ./start.sh          # 使用指定端口启动"
    echo "  REBUILD_FRONTEND=true ./start.sh  # 强制重新构建前端"
    echo "  PORT=8000 REBUILD_FRONTEND=true ./start.sh  # 组合使用"
    echo ""
    echo "环境选择："
    echo "  - 交互模式：会询问使用哪种Python环境（推荐新手）"
    echo "  - 自动模式：自动检测并使用当前激活的环境"
    echo ""
    exit 0
}

# 选择Python环境
select_python_env() {
    # 检测已存在的环境
    HAS_CONDA=false
    HAS_VENV=false
    HAS_SYSTEM=true
    
    if [ -n "$CONDA_DEFAULT_ENV" ]; then
        HAS_CONDA=true
        DETECTED_ENV="conda"
        DETECTED_ENV_NAME="$CONDA_DEFAULT_ENV"
    elif [ -n "$VIRTUAL_ENV" ]; then
        HAS_VENV=true
        DETECTED_ENV="venv"
        DETECTED_ENV_NAME=$(basename "$VIRTUAL_ENV")
    fi
    
    # 检查是否有conda命令
    if command -v conda &> /dev/null; then
        HAS_CONDA_CMD=true
    else
        HAS_CONDA_CMD=false
    fi
    
    # 检查是否已有venv目录
    if [ -d "venv" ] || [ -d ".venv" ]; then
        HAS_VENV_DIR=true
    else
        HAS_VENV_DIR=false
    fi
    
    # 如果使用 --auto 参数，自动选择
    if [ "$1" = "--auto" ]; then
        if [ "$HAS_CONDA" = true ]; then
            SELECTED_ENV="conda"
            SELECTED_ENV_NAME="$CONDA_DEFAULT_ENV"
            print_info "自动选择: Conda环境 ($CONDA_DEFAULT_ENV)"
            return 0
        elif [ "$HAS_VENV" = true ]; then
            SELECTED_ENV="venv"
            SELECTED_ENV_NAME=$(basename "$VIRTUAL_ENV")
            print_info "自动选择: venv环境 ($SELECTED_ENV_NAME)"
            return 0
        else
            SELECTED_ENV="system"
            print_warning "自动选择: 系统Python（建议使用虚拟环境）"
            return 0
        fi
    fi
    
    # 交互式选择
    echo ""
    print_header "选择Python环境"
    
    # 如果有检测到的环境，优先显示
    if [ "$HAS_CONDA" = true ] || [ "$HAS_VENV" = true ]; then
        print_success "检测到已激活的环境: $DETECTED_ENV ($DETECTED_ENV_NAME)"
        echo ""
        echo "  1) 使用当前环境 ($DETECTED_ENV) [推荐]"
        echo "  2) 创建新的venv环境 [新手推荐]"
        if [ "$HAS_CONDA_CMD" = true ]; then
            echo "  3) 创建新的conda环境"
        fi
        echo "  4) 使用系统Python [不推荐]"
        echo ""
        read -p "请选择 (1-4，直接回车使用选项1): " choice
        choice=${choice:-1}
    else
        print_info "未检测到已激活的Python环境"
        echo ""
        echo "  1) 创建venv环境 [新手推荐，最简单]"
        if [ "$HAS_CONDA_CMD" = true ]; then
            echo "  2) 创建conda环境"
        fi
        echo "  3) 使用系统Python [不推荐]"
        echo ""
        read -p "请选择 (1-3，直接回车使用选项1): " choice
        choice=${choice:-1}
        
        # 调整选项编号
        if [ "$HAS_CONDA_CMD" = true ]; then
            # 有conda: 1=venv, 2=conda, 3=system
            if [ "$choice" = "2" ]; then choice="3"; fi
            if [ "$choice" = "3" ]; then choice="4"; fi
        else
            # 无conda: 1=venv, 2=system
            if [ "$choice" = "2" ]; then choice="4"; fi
        fi
    fi
    
    case $choice in
        1)
            if [ "$HAS_CONDA" = true ] || [ "$HAS_VENV" = true ]; then
                SELECTED_ENV="$DETECTED_ENV"
                SELECTED_ENV_NAME="$DETECTED_ENV_NAME"
                print_success "使用当前环境: $SELECTED_ENV ($SELECTED_ENV_NAME)"
            else
                # 创建venv
                SELECTED_ENV="venv"
                create_venv_env
            fi
            ;;
        2)
            if [ "$HAS_CONDA" = true ] || [ "$HAS_VENV" = true ]; then
                # 创建venv
                SELECTED_ENV="venv"
                create_venv_env
            else
                # 创建conda（如果可用）
                if [ "$HAS_CONDA_CMD" = true ]; then
                    SELECTED_ENV="conda"
                    create_conda_env
                else
                    print_error "未找到conda命令"
                    exit 1
                fi
            fi
            ;;
        3)
            if [ "$HAS_CONDA_CMD" = true ]; then
                SELECTED_ENV="conda"
                create_conda_env
            else
                SELECTED_ENV="system"
                print_warning "使用系统Python（不推荐）"
            fi
            ;;
        4)
            SELECTED_ENV="system"
            print_warning "使用系统Python（不推荐）"
            ;;
        *)
            print_error "无效选择"
            exit 1
            ;;
    esac
}

# 创建venv环境
create_venv_env() {
    VENV_DIR="venv"
    if [ -d "$VENV_DIR" ]; then
        print_info "venv目录已存在: $VENV_DIR"
        read -p "是否使用现有venv? (y/n，默认y): " use_existing
        use_existing=${use_existing:-y}
        if [ "$use_existing" != "y" ] && [ "$use_existing" != "Y" ]; then
            print_info "删除旧venv并创建新的..."
            rm -rf "$VENV_DIR"
        else
            print_success "使用现有venv"
            SELECTED_ENV_NAME="venv"
            # 设置PYTHON_CMD
            PYTHON_CMD="$VENV_DIR/bin/python"
            if [ ! -f "$PYTHON_CMD" ]; then
                print_error "venv中的Python不存在，请重新创建"
                rm -rf "$VENV_DIR"
            else
                return 0
            fi
        fi
    fi
    
    print_info "创建venv环境..."
    $TEMP_PYTHON_CMD -m venv "$VENV_DIR"
    
    if [ $? -eq 0 ]; then
        print_success "venv环境创建成功"
        print_info "正在激活venv环境..."
        source "$VENV_DIR/bin/activate"
        SELECTED_ENV_NAME="venv"
        # 更新PYTHON_CMD
        PYTHON_CMD="$VENV_DIR/bin/python"
    else
        print_error "venv环境创建失败"
        exit 1
    fi
}

# 创建conda环境
create_conda_env() {
    ENV_NAME="evaluation_viewer"
    print_info "创建conda环境: $ENV_NAME"
    
    # 检查环境是否已存在
    if conda env list | grep -q "^$ENV_NAME "; then
        print_info "conda环境已存在: $ENV_NAME"
        read -p "是否使用现有环境? (y/n，默认y): " use_existing
        use_existing=${use_existing:-y}
        if [ "$use_existing" = "y" ] || [ "$use_existing" = "Y" ]; then
            print_info "激活conda环境..."
            eval "$(conda shell.bash hook)" 2>/dev/null || true
            conda activate "$ENV_NAME"
            SELECTED_ENV_NAME="$ENV_NAME"
            PYTHON_CMD=$(command -v python)
            return 0
        fi
    fi
    
    print_info "正在创建conda环境（这可能需要几分钟）..."
    conda create -n "$ENV_NAME" python=3.10 -y
    
    if [ $? -eq 0 ]; then
        print_success "conda环境创建成功"
        print_info "激活conda环境..."
        eval "$(conda shell.bash hook)" 2>/dev/null || true
        conda activate "$ENV_NAME"
        SELECTED_ENV_NAME="$ENV_NAME"
        PYTHON_CMD=$(command -v python)
    else
        print_error "conda环境创建失败"
        exit 1
    fi
}

AUTO_MODE=false
if [ "$1" = "--auto" ]; then
    AUTO_MODE=true
    shift
elif [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    show_help
fi

print_header "🚀 启动评测结果展示系统"

# 配置参数
PORT=${PORT:-5000}
REBUILD_FRONTEND=${REBUILD_FRONTEND:-false}

print_info "服务端口: $PORT"

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

cd "$SCRIPT_DIR"

# 首先检查是否有Python
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    print_error "未找到Python，请确保Python 3.8+已安装"
    exit 1
fi

# 临时Python命令（用于环境检测）
TEMP_PYTHON_CMD=$(command -v python3 2>/dev/null || command -v python 2>/dev/null)

# 选择Python环境
if [ "$AUTO_MODE" = true ]; then
    select_python_env "--auto"
else
    select_python_env
fi

# 检查Python环境
print_info "检查Python环境..."

# 根据选择的环境设置Python命令
case $SELECTED_ENV in
    conda)
        if [ -n "$CONDA_DEFAULT_ENV" ]; then
            PYTHON_CMD=$(command -v python 2>/dev/null || command -v python3 2>/dev/null)
            ENV_TYPE="conda"
            ENV_NAME="$CONDA_DEFAULT_ENV"
        else
            # 如果选择了conda但未激活，尝试激活
            if [ -n "$SELECTED_ENV_NAME" ]; then
                eval "$(conda shell.bash hook)" 2>/dev/null || true
                conda activate "$SELECTED_ENV_NAME" 2>/dev/null || true
                PYTHON_CMD=$(command -v python 2>/dev/null || command -v python3 2>/dev/null)
                ENV_TYPE="conda"
                ENV_NAME="$SELECTED_ENV_NAME"
            fi
        fi
        ;;
    venv)
        if [ -n "$VIRTUAL_ENV" ]; then
            PYTHON_CMD="$VIRTUAL_ENV/bin/python"
            ENV_TYPE="venv"
            ENV_NAME=$(basename "$VIRTUAL_ENV")
        elif [ -f "venv/bin/python" ]; then
            # 使用项目目录下的venv
            source venv/bin/activate 2>/dev/null || true
            PYTHON_CMD="venv/bin/python"
            ENV_TYPE="venv"
            ENV_NAME="venv"
        else
            PYTHON_CMD=$(command -v python3 2>/dev/null || command -v python 2>/dev/null)
            ENV_TYPE="venv"
            ENV_NAME="$SELECTED_ENV_NAME"
        fi
        ;;
    system)
        PYTHON_CMD=$(command -v python3 2>/dev/null || command -v python 2>/dev/null)
        ENV_TYPE="system"
        ENV_NAME=""
        ;;
    *)
        PYTHON_CMD=$(command -v python3 2>/dev/null || command -v python 2>/dev/null)
        ENV_TYPE="system"
        ENV_NAME=""
        ;;
esac

if [ -z "$PYTHON_CMD" ] || [ ! -f "$PYTHON_CMD" ]; then
    print_error "未找到Python，请确保Python 3.8+已安装"
    exit 1
fi

# 获取Python版本
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    print_error "Python版本过低，需要Python 3.8+，当前版本: $PYTHON_VERSION"
    exit 1
fi

# 显示环境信息
if [ "$ENV_TYPE" != "system" ]; then
    print_success "Python版本: $PYTHON_VERSION (环境: $ENV_TYPE - $ENV_NAME)"
    print_info "Python路径: $PYTHON_CMD"
else
    print_success "Python版本: $PYTHON_VERSION (系统环境)"
    print_warning "建议使用虚拟环境（conda/venv）来管理依赖"
fi

# 检查前端构建产物
NEED_NODE=false
if [ ! -d "$FRONTEND_DIR/dist" ] || [ "$REBUILD_FRONTEND" = "true" ]; then
    NEED_NODE=true
    print_info "需要构建前端，检查Node.js环境..."
    
    if ! command -v node &> /dev/null; then
        print_error "未找到Node.js，但需要构建前端"
        print_info "请安装Node.js 16+，或使用已包含dist目录的版本"
        exit 1
    fi
    
    NODE_VERSION=$(node --version | sed 's/v//')
    NODE_MAJOR=$(echo $NODE_VERSION | cut -d. -f1)
    
    if [ "$NODE_MAJOR" -lt 16 ]; then
        print_error "Node.js版本过低，需要Node.js 16+，当前版本: $NODE_VERSION"
        exit 1
    fi
    
    print_success "Node.js版本: $NODE_VERSION"
    
    # 检查npm
    if ! command -v npm &> /dev/null; then
        print_error "未找到npm，请确保npm已安装"
        exit 1
    fi
    
    print_success "npm版本: $(npm --version)"
else
    print_success "前端已构建，跳过Node.js检查"
fi

# 检查Python依赖
print_info "检查Python依赖..."
if [ ! -f "requirements.txt" ]; then
    print_error "未找到requirements.txt文件"
    exit 1
fi

# 确定pip命令
PIP_CMD="$PYTHON_CMD -m pip"
if [ "$ENV_TYPE" = "conda" ]; then
    # Conda环境优先使用conda install，但也可以使用pip
    if command -v conda &> /dev/null; then
        print_info "检测到Conda环境，使用pip安装（也可使用: conda install -c conda-forge flask pandas openpyxl）"
    fi
fi

# 检查是否安装了必要的Python包
if ! $PYTHON_CMD -c "import flask" 2>/dev/null; then
    print_warning "Flask未安装，正在安装Python依赖..."
    print_info "使用: $PIP_CMD"
    
    # 升级pip
    $PIP_CMD install --upgrade pip -q
    
    # 安装依赖
    $PIP_CMD install -r requirements.txt -q
    
    if [ $? -eq 0 ]; then
        print_success "Python依赖安装完成"
    else
        print_error "Python依赖安装失败"
        echo ""
        print_info "请手动安装依赖："
        if [ "$ENV_TYPE" = "conda" ]; then
            echo "   conda install -c conda-forge flask pandas openpyxl"
            echo "   或"
        fi
        echo "   $PIP_CMD install -r requirements.txt"
        exit 1
    fi
else
    print_success "Python依赖已就绪"
fi

# 检查pandas（可选但推荐）
if ! $PYTHON_CMD -c "import pandas" 2>/dev/null; then
    print_warning "pandas未安装，Excel读取功能将不可用"
    print_info "如需使用Excel功能，请运行："
    if [ "$ENV_TYPE" = "conda" ]; then
        echo "   conda install -c conda-forge pandas openpyxl"
        echo "   或"
    fi
    echo "   $PIP_CMD install pandas openpyxl"
fi

# 检查端口是否被占用
print_info "检查端口 $PORT 是否可用..."
if lsof -i :$PORT > /dev/null 2>&1 || netstat -an 2>/dev/null | grep -q ":$PORT.*LISTEN"; then
    print_error "端口 $PORT 已被占用"
    echo ""
    print_info "查找占用端口的进程："
    echo "   lsof -i :$PORT"
    echo "   或"
    echo "   netstat -an | grep $PORT"
    echo ""
    print_info "停止占用端口的进程："
    echo "   kill -9 \$(lsof -t -i :$PORT)"
    echo ""
    print_info "或使用其他端口启动："
    echo "   PORT=8000 ./start.sh"
    exit 1
fi

print_success "端口 $PORT 可用"

# 检查并构建前端
print_info "检查前端构建..."
cd "$FRONTEND_DIR"

if [ ! -d "dist" ] || [ "$REBUILD_FRONTEND" = "true" ]; then
    if [ "$REBUILD_FRONTEND" = "true" ] && [ -d "dist" ]; then
        print_info "强制重新构建前端..."
        rm -rf dist
    else
        print_info "前端未构建，正在构建..."
    fi

    # 检查Node.js（如果之前没检查过）
    if [ "$NEED_NODE" != "true" ]; then
        if ! command -v node &> /dev/null; then
            print_error "未找到Node.js，无法构建前端"
            print_info "请安装Node.js 16+，或使用已包含dist目录的版本"
            exit 1
        fi
    fi

    if [ ! -d "node_modules" ]; then
        print_info "安装前端依赖..."
        npm install --no-fund --no-audit
        print_success "前端依赖安装完成"
    fi

    print_info "构建前端应用（这可能需要几分钟）..."
    npm run build

    if [ $? -ne 0 ]; then
        print_error "前端构建失败"
        print_info "请手动构建：cd frontend && npm run build"
        exit 1
    fi

    print_success "前端构建成功"
else
    print_success "前端已构建（跳过构建步骤）"
    print_info "如需重新构建，请运行: REBUILD_FRONTEND=true ./start.sh"
fi

cd "$SCRIPT_DIR"

# 启动Flask服务
print_info "启动Flask服务 (端口 $PORT)..."
export PORT=$PORT
$PYTHON_CMD app.py &
BACKEND_PID=$!

# 等待后端启动
print_info "等待服务启动..."
sleep 3

# 检查后端是否启动成功
if ! curl -s http://localhost:$PORT/api/stats/overview > /dev/null 2>&1; then
    print_error "后端服务启动失败或无法访问"
    echo ""
    print_info "可能的原因："
    echo "   - 端口权限问题"
    echo "   - Flask应用启动错误"
    echo "   - 防火墙阻止访问"
    echo ""
    print_info "诊断步骤："
    echo "   1. 检查Flask日志输出"
    echo "   2. 手动启动测试: PORT=$PORT python app.py"
    echo "   3. 检查端口监听: lsof -i :$PORT"
    echo ""
    
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

print_success "Flask服务已启动"

# 显示启动信息
echo ""
print_header "🎉 服务启动完成"
echo -e "${GREEN}🌐 完整应用: http://localhost:$PORT${NC}"
echo -e "${GREEN}🔌 Flask API: http://localhost:$PORT/api/${NC}"
echo ""
print_info "按 Ctrl+C 停止服务"
echo ""

# 清理函数
cleanup() {
    echo ""
    print_info "正在停止服务..."
    kill $BACKEND_PID 2>/dev/null || true
    wait $BACKEND_PID 2>/dev/null || true
    print_success "服务已停止"
    exit 0
}

# 捕获中断信号
trap cleanup INT TERM

# 保持脚本运行
wait $BACKEND_PID

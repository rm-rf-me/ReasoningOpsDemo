# 评测结果展示系统

一个基于 Flask + Vue 3 的全栈 Web 应用，用于可视化和分析模型评测结果。

## 📋 功能特性

- 📊 **评测结果展示**：列表展示、详情查看、统计概览
- 🔍 **智能筛选**：支持按场景分类、预测结果、关键词搜索
- 📁 **Excel 关联**：自动匹配并加载 Excel 上下文数据
- 🎯 **导航浏览**：支持在筛选结果中上下条浏览
- 📈 **数据统计**：准确率、F1 分数等指标展示

## 📦 环境要求

- **Python 3.8+**（必需）
- **Node.js 16+**（可选，仅当需要重新构建前端时）

> 💡 **提示**：如果项目已包含 `frontend/dist` 目录，则无需安装 Node.js，可直接运行。

## 🚀 快速开始

### 方式一：最简单（推荐新手）

如果项目已包含构建好的前端文件，只需三步：

```bash
# 1. 克隆项目
git clone <repository-url>
cd ReasoningDemo/evaluation_viewer

# 2. 创建并激活 Python 虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 运行启动脚本（会自动安装依赖）
./start.sh
```

启动脚本会：
- ✅ 自动检测 Python 环境
- ✅ 自动安装 Python 依赖
- ✅ 自动启动服务

启动成功后访问：**http://localhost:5000**

### 方式二：需要构建前端

如果 `frontend/dist` 目录不存在，需要先安装 Node.js：

#### 安装 Node.js

**macOS**:
```bash
brew install node
```

**Linux (Ubuntu/Debian)**:
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

**Windows**: 访问 [nodejs.org](https://nodejs.org/) 下载安装

#### 然后运行

```bash
# 1. 克隆项目
git clone <repository-url>
cd ReasoningDemo/evaluation_viewer

# 2. 创建 Python 环境
python3 -m venv venv
source venv/bin/activate

# 3. 启动（会自动构建前端）
./start.sh
```

## 📖 使用说明

### 启动选项

```bash
# 交互式启动（推荐新手，会询问Python环境）
./start.sh

# 自动模式（使用当前激活的环境）
./start.sh --auto

# 指定端口
PORT=8000 ./start.sh

# 查看帮助
./start.sh --help
```

### 数据配置

1. **扫描 Excel 文件**：点击右上角"上传数据" → 输入 Excel 目录路径 → 点击"扫描Excel文件"
2. **加载评测结果**：输入 JSONL 文件路径 → 点击"加载结果文件"
3. **开始分析**：确认数据加载成功后 → 点击"开始分析"

### 数据格式

#### 评测结果文件（JSONL）

每行一个 JSON 对象：

```json
{
  "input": "模型输入内容",
  "expected_output": "人工标注输出",
  "model_output": "模型输出",
  "predicted_label": "convergent",
  "reference_label": "convergent",
  "correct": true,
  "meta": {
    "category": "场景分类",
    "scenario_id": "Excel文件名_Sheet名"
  }
}
```

#### Excel 文件

- 支持 `.xlsx` 和 `.xls` 格式
- `scenario_id` 格式：`Excel文件名_Sheet名`（最后一个下划线分隔）

## 🐛 常见问题

### 端口被占用

```bash
# 使用其他端口
PORT=8000 ./start.sh
```

### Python 依赖安装失败

```bash
# 使用国内镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Excel 功能不可用

```bash
pip install pandas openpyxl
```

### 前端构建失败

```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

---

💡 **提示**：首次使用建议运行 `./start.sh --help` 查看帮助信息

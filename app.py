#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
评测结果展示系统 - Flask全栈应用
简化版：同时提供前端页面和后端API
"""

import os
import logging
import hashlib
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
import json as json_lib

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Excel处理库
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    logger.warning("pandas未安装，Excel读取功能将不可用。请运行: pip install pandas openpyxl")

# 创建Flask应用
app = Flask(__name__,
            static_folder='frontend/dist',
            template_folder='frontend/dist')

# 简单的CORS中间件
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

# 全局数据存储
evaluation_results = []
excel_dir_path = None  # 保存Excel目录路径
excel_files_list = []  # 保存扫描到的Excel文件列表
results_file_path = None  # 保存结果文件路径
filter_options = {
    "categories": [],
    "scenarios": [],
    "correctness_options": ["correct", "incorrect", "parse_failed"]
}


def load_evaluation_results(file_path):
    """加载评测结果"""
    global evaluation_results, filter_options

    results = []
    categories = set()
    scenarios = set()

    try:
        if not Path(file_path).exists():
            logger.warning(f"文件不存在: {file_path}")
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    result = json_lib.loads(line)
                    # 为每个结果生成唯一的 alarm_id（如果不存在）
                    if 'alarm_id' not in result:
                        # 使用内容的哈希值生成唯一ID
                        content_str = json_lib.dumps(result, sort_keys=True)
                        result['alarm_id'] = hashlib.md5(content_str.encode()).hexdigest()[:16]
                    results.append(result)

                    # 收集筛选选项
                    if 'meta' in result:
                        categories.add(result['meta'].get('category', ''))
                        scenarios.add(result['meta'].get('scenario_id', ''))

                except json_lib.JSONDecodeError as e:
                    logger.warning(f"解析第{line_num}行失败: {e}")
                    continue

        evaluation_results[:] = results
        filter_options['categories'] = sorted(list(categories))
        filter_options['scenarios'] = sorted(list(scenarios))

        logger.info(f"成功加载 {len(results)} 条评测结果")

    except Exception as e:
        logger.error(f"加载评测结果失败: {e}")


def scan_excel_files(directory):
    """扫描Excel文件"""
    excel_files = []
    try:
        if Path(directory).exists():
            excel_files = list(Path(directory).glob("**/*.xlsx")) + list(Path(directory).glob("**/*.xls"))
    except Exception as e:
        logger.warning(f"扫描Excel文件失败: {e}")

    return excel_files


@app.route('/')
def index():
    """主页"""
    try:
        # 直接返回HTML文件内容
        html_path = Path('frontend/dist/index.html')
        if html_path.exists():
            with open(html_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            # 返回一个简单的HTML页面
            return '''
<!DOCTYPE html>
<html>
<head>
    <title>评测结果展示系统</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 800px; margin: 0 auto; }
        .alert { padding: 15px; border-radius: 4px; margin: 15px 0; }
        .info { background: #e6f7ff; border: 1px solid #91d5ff; color: #1890ff; }
        .error { background: #fff2f0; border: 1px solid #ffccc7; color: #ff4d4f; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 评测结果展示系统</h1>
        <div class="alert error">
            <strong>错误：</strong>前端文件未找到，请先构建前端应用。
            <br><br>
            运行命令：<code>cd frontend && npm run build</code>
        </div>
        <div class="alert info">
            <strong>后端状态：</strong>Flask服务运行正常，可以通过API访问数据。
        </div>
    </div>
</body>
</html>
'''
    except Exception as e:
        return f'<h1>错误</h1><p>{str(e)}</p>'


@app.route('/test')
def test_page():
    """API测试页面"""
    try:
        test_html_path = Path('test_api.html')
        if test_html_path.exists():
            with open(test_html_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            return "Test page not found", 404
    except Exception as e:
        return f"Error loading test page: {e}", 500


@app.route('/<path:filename>')
def serve_static(filename):
    """提供静态文件"""
    try:
        # 首先尝试从前端dist目录提供
        frontend_path = Path('frontend/dist') / filename
        if frontend_path.exists():
            return send_from_directory('frontend/dist', filename)
        # 然后尝试默认的静态文件夹
        return send_from_directory(app.static_folder, filename)
    except Exception as e:
        logger.error(f"提供静态文件失败 {filename}: {e}")
        return "File not found", 404


# 文件上传功能已移除，改为路径扫描方式

@app.route('/api/scan/excel', methods=['POST'])
def scan_excel():
    """扫描Excel文件（只返回文件名列表，不读取内容）"""
    global excel_dir_path, excel_files_list
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400

        excel_dir = data.get('excel_dir', '').strip()
        if not excel_dir:
            return jsonify({'error': '必须提供Excel目录路径'}), 400

        # 扫描Excel文件
        excel_files = scan_excel_files(excel_dir)
        excel_file_paths = [str(f) for f in excel_files]
        
        # 保存Excel目录路径和文件列表
        excel_dir_path = excel_dir
        excel_files_list = excel_file_paths

        return jsonify({
            'message': f'扫描完成，找到 {len(excel_file_paths)} 个Excel文件',
            'excel_files': excel_file_paths,
            'count': len(excel_file_paths)
        })

    except Exception as e:
        logger.error(f"扫描Excel文件失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/load/results', methods=['POST'])
def load_results():
    """加载评测结果文件"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400

        results_path = data.get('results_path', '').strip()
        if not results_path:
            return jsonify({'error': '必须提供评测结果文件路径'}), 400

        # 保存结果文件路径
        global results_file_path
        results_file_path = results_path

        # 加载评测结果
        load_evaluation_results(results_path)
        results_count = len(evaluation_results)

        # 收集分类信息
        categories = set()
        for result in evaluation_results:
            if 'meta' in result and 'category' in result['meta']:
                categories.add(result['meta']['category'])

        return jsonify({
            'message': f'文件加载成功，共 {results_count} 条记录',
            'total_records': results_count,
            'categories': sorted(list(categories))
        })

    except Exception as e:
        logger.error(f"加载评测结果文件失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/analysis/start', methods=['POST'])
def start_analysis():
    """开始分析（Excel已扫描，结果已加载）"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400

        # 此时数据已经加载，只需要确认
        results_count = len(evaluation_results)
        
        # 获取Excel文件列表（如果之前扫描过）
        excel_dir = data.get('excel_dir', '').strip()
        excel_files = []
        if excel_dir:
            excel_files = [str(f) for f in scan_excel_files(excel_dir)]

        return jsonify({
            'message': '分析完成',
            'results_count': results_count,
            'excel_files_count': len(excel_files)
        })

    except Exception as e:
        logger.error(f"开始分析失败: {e}")
        return jsonify({'error': str(e)}), 500


# /api/scan/load API已废弃，改为分步骤的API：
# 1. /api/scan/excel - 扫描Excel文件
# 2. /api/load/results - 加载结果文件
# 3. /api/analysis/start - 开始分析


@app.route('/api/results')
def get_results():
    """获取评测结果列表"""
    try:
        page = int(request.args.get('page', 1))
        size = int(request.args.get('size', 20))
        search = request.args.get('search', '').strip()
        category = request.args.get('category', '').strip()
        correctness = request.args.get('correctness', '').strip()

        # 筛选数据
        filtered_results = evaluation_results

        if search:
            search_lower = search.lower()
            filtered_results = [
                r for r in filtered_results
                if search_lower in r.get('input', '').lower() or
                   search_lower in r.get('expected_output', '').lower() or
                   search_lower in r.get('model_output', '').lower()
            ]

        if category:
            filtered_results = [
                r for r in filtered_results
                if r.get('meta', {}).get('category') == category
            ]

        if correctness:
            if correctness == "correct":
                filtered_results = [r for r in filtered_results if r.get('correct', False)]
            elif correctness == "incorrect":
                filtered_results = [r for r in filtered_results if not r.get('correct', True) and r.get('predicted_label') is not None]
            elif correctness == "parse_failed":
                filtered_results = [r for r in filtered_results if r.get('predicted_label') is None]

        # 分页
        start_idx = (page - 1) * size
        end_idx = start_idx + size
        paginated_results = filtered_results[start_idx:end_idx]

        return jsonify({
            'results': paginated_results,
            'pagination': {
                'page': page,
                'size': size,
                'total': len(filtered_results),
                'pages': (len(filtered_results) + size - 1) // size
            },
            'filters': {
                'search': search,
                'category': category,
                'correctness': correctness
            }
        })

    except Exception as e:
        logger.error(f"获取结果列表失败: {e}")
        return jsonify({'error': str(e)}), 500


def read_excel_sheet(excel_file_path, sheet_name=None):
    """读取Excel文件的工作表"""
    if not PANDAS_AVAILABLE:
        return None
    
    try:
        excel_path = Path(excel_file_path)
        if not excel_path.exists():
            logger.warning(f"Excel文件不存在: {excel_file_path}")
            return None
        
        # 读取Excel文件
        if sheet_name:
            df = pd.read_excel(excel_path, sheet_name=sheet_name)
        else:
            # 读取第一个工作表
            df = pd.read_excel(excel_path, sheet_name=0)
        
        # 将NaN值替换为None，以便JSON序列化
        df = df.fillna('')
        
        # 转换为字典列表，确保所有值都是可序列化的
        records = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                # 处理pandas的特殊类型
                if pd.isna(value):
                    record[col] = ''
                elif isinstance(value, (pd.Timestamp, pd.DatetimeTZDtype)):
                    record[col] = str(value)
                else:
                    record[col] = value
            records.append(record)
        
        return records
    
    except Exception as e:
        logger.warning(f"读取Excel文件失败 {excel_file_path}: {e}")
        return None


def get_excel_context_for_alarm(alarm_id, result):
    """根据告警ID和结果信息，从Excel文件中读取上下文"""
    global excel_dir_path, excel_files_list
    
    if not excel_dir_path or not excel_files_list:
        return {
            'error': 'Excel文件路径未配置或未扫描到Excel文件。请先在列表页配置Excel文件路径。',
            'excel_dir_path': excel_dir_path,
            'excel_files_count': len(excel_files_list) if excel_files_list else 0
        }
    
    if not PANDAS_AVAILABLE:
        return {
            'error': 'pandas未安装，无法读取Excel文件',
            'excel_files_available': excel_files_list
        }
    
    try:
        # 根据结果的meta信息找到对应的Excel文件
        excel_file_path = None
        
        if 'meta' in result:
            meta = result['meta']
            # 尝试从meta中获取Excel文件路径
            if 'excel_file_path' in meta:
                excel_file_path = meta['excel_file_path']
            elif 'scenario_id' in meta:
                # 根据scenario_id匹配Excel文件
                # scenario_id格式: Excel文件名_Sheet名
                scenario_id = meta['scenario_id']
                logger.info(f"查找Excel文件，scenario_id: {scenario_id}")
                
                # 解析scenario_id: 格式为 "Excel文件名_Sheet名"（从最后一个下划线拆分）
                # 例如："冷塔加减机_BJ4-25年BA报警-冷却塔加减机52个-AIOS_4.7-1"
                # Excel文件名：冷塔加减机_BJ4-25年BA报警-冷却塔加减机52个-AIOS
                # Sheet名：4.7-1
                last_underscore_index = scenario_id.rfind('_')
                if last_underscore_index > 0:
                    excel_file_name = scenario_id[:last_underscore_index]  # 获取Excel文件名部分
                    sheet_name = scenario_id[last_underscore_index + 1:]  # 获取Sheet名部分
                    logger.info(f"解析scenario_id - Excel文件名: {excel_file_name}, Sheet名: {sheet_name}")
                else:
                    excel_file_name = scenario_id
                    sheet_name = None
                    logger.info(f"scenario_id不包含下划线，使用完整名称: {excel_file_name}")
                
                # 匹配Excel文件
                for excel_file in excel_files_list:
                    excel_file_path_obj = Path(excel_file)
                    excel_file_stem = excel_file_path_obj.stem  # 文件名（不含扩展名）
                    
                    # 匹配逻辑：文件名包含excel_file_name，或者stem等于excel_file_name
                    if excel_file_name in excel_file_stem or excel_file_stem == excel_file_name:
                        excel_file_path = excel_file
                        logger.info(f"找到匹配的Excel文件: {excel_file_path}")
                        break
        
        if not excel_file_path:
            # 如果没有找到匹配的Excel文件，返回错误信息
            excel_file_name_hint = ''
            if 'meta' in result and 'scenario_id' in result['meta']:
                scenario_id = result['meta']['scenario_id']
                last_underscore_index = scenario_id.rfind('_')
                if last_underscore_index > 0:
                    excel_file_name_hint = scenario_id[:last_underscore_index]
                else:
                    excel_file_name_hint = scenario_id
            
            return {
                'error': f'未找到匹配的Excel文件。期望的文件名包含: {excel_file_name_hint}',
                'excel_file_name_expected': excel_file_name_hint,
                'excel_files_available': [str(f) for f in excel_files_list[:10]],  # 只返回前10个作为参考
                'excel_files_count': len(excel_files_list)
            }
        
        # 读取Excel文件内容（读取整个sheet，不限制行数）
        # 如果scenario_id包含下划线，尝试读取对应的sheet（从最后一个下划线拆分）
        sheet_name_to_read = None
        if 'meta' in result and 'scenario_id' in result['meta']:
            scenario_id = result['meta']['scenario_id']
            last_underscore_index = scenario_id.rfind('_')
            if last_underscore_index > 0:
                sheet_name_to_read = scenario_id[last_underscore_index + 1:]
                logger.info(f"尝试读取Sheet: {sheet_name_to_read}")
        
        excel_data = read_excel_sheet(excel_file_path, sheet_name=sheet_name_to_read)
        
        if excel_data:
            return {
                'excel_file': excel_file_path,
                'excel_dir': excel_dir_path,
                'data': excel_data,  # 返回所有数据
                'total_rows': len(excel_data)
            }
        else:
            return {
                'excel_file': excel_file_path,
                'excel_dir': excel_dir_path,
                'error': '无法读取Excel文件内容，请确认文件格式是否正确'
            }
        
    except Exception as e:
        logger.warning(f"读取Excel上下文失败: {e}")
        return {
            'error': str(e),
            'excel_file': excel_file_path if 'excel_file_path' in locals() else None
        }


@app.route('/api/results/<alarm_id>')
def get_result_detail(alarm_id):
    """获取单个结果详情（不自动加载Excel）"""
    try:
        result = next((r for r in evaluation_results if r.get('alarm_id') == alarm_id), None)
        if not result:
            return jsonify({'error': '结果不存在'}), 404

        # 直接返回结果，不加载Excel（Excel通过单独的API加载）
        return jsonify(result)

    except Exception as e:
        logger.error(f"获取结果详情失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/results/<alarm_id>/excel-context')
def get_excel_context(alarm_id):
    """获取Excel上下文（按需加载）"""
    try:
        result = next((r for r in evaluation_results if r.get('alarm_id') == alarm_id), None)
        if not result:
            return jsonify({'error': '结果不存在'}), 404

        # 读取Excel上下文
        excel_context = get_excel_context_for_alarm(alarm_id, result)
        
        if excel_context and 'data' in excel_context:
            return jsonify({
                'data': excel_context['data'],
                'total_rows': excel_context.get('total_rows', len(excel_context['data'])),
                'excel_file': excel_context.get('excel_file'),
                'excel_dir': excel_context.get('excel_dir')
            })
        elif excel_context and 'error' in excel_context:
            # 返回详细的错误信息
            error_response = {'error': excel_context['error']}
            # 如果包含额外信息，一并返回
            if 'excel_file_name_expected' in excel_context:
                error_response['excel_file_name_expected'] = excel_context['excel_file_name_expected']
            if 'excel_files_available' in excel_context:
                error_response['excel_files_available'] = excel_context['excel_files_available']
            if 'excel_files_count' in excel_context:
                error_response['excel_files_count'] = excel_context['excel_files_count']
            return jsonify(error_response), 400
        else:
            return jsonify({'error': '无法加载Excel上下文：Excel文件路径未配置或未找到匹配的文件'}), 404

    except Exception as e:
        logger.error(f"获取Excel上下文失败: {e}")
        return jsonify({'error': f'加载Excel上下文时发生错误: {str(e)}'}), 500


@app.route('/api/results/<alarm_id>/navigation')
def get_navigation_info(alarm_id):
    """获取导航信息（基于当前筛选条件）"""
    try:
        # 获取筛选参数（与列表页保持一致）
        search = request.args.get('search', '').strip()
        category = request.args.get('category', '').strip()
        correctness = request.args.get('correctness', '').strip()
        
        # 应用相同的筛选逻辑
        filtered_results = evaluation_results

        if search:
            search_lower = search.lower()
            filtered_results = [
                r for r in filtered_results
                if search_lower in r.get('input', '').lower() or
                   search_lower in r.get('expected_output', '').lower() or
                   search_lower in r.get('model_output', '').lower()
            ]

        if category:
            filtered_results = [
                r for r in filtered_results
                if r.get('meta', {}).get('category') == category
            ]

        if correctness:
            if correctness == "correct":
                filtered_results = [r for r in filtered_results if r.get('correct', False)]
            elif correctness == "incorrect":
                filtered_results = [r for r in filtered_results if not r.get('correct', True) and r.get('predicted_label') is not None]
            elif correctness == "parse_failed":
                filtered_results = [r for r in filtered_results if r.get('predicted_label') is None]

        # 在筛选后的结果中查找当前告警
        total = len(filtered_results)
        current_index = next((i for i, r in enumerate(filtered_results) if r.get('alarm_id') == alarm_id), -1)

        if current_index == -1:
            return jsonify({
                'current': alarm_id,
                'previous': None,
                'next': None,
                'total': total,
                'current_index': 0,
                'filters': {
                    'search': search,
                    'category': category,
                    'correctness': correctness
                }
            })

        return jsonify({
            'current': alarm_id,
            'previous': filtered_results[current_index - 1].get('alarm_id') if current_index > 0 else None,
            'next': filtered_results[current_index + 1].get('alarm_id') if current_index < total - 1 else None,
            'total': total,
            'current_index': current_index + 1,
            'filters': {
                'search': search,
                'category': category,
                'correctness': correctness
            }
        })

    except Exception as e:
        logger.error(f"获取导航信息失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats/overview')
def get_overview_stats():
    """获取整体统计信息"""
    try:
        if not evaluation_results:
            return jsonify({
                'total_results': 0,
                'correct_predictions': 0,
                'incorrect_predictions': 0,
                'parse_failures': 0,
                'accuracy': 0.0,
                'precision': 0.0,
                'recall': 0.0,
                'f1_score': 0.0
            })

        total = len(evaluation_results)
        correct = sum(1 for r in evaluation_results if r.get('correct', False))
        incorrect = sum(1 for r in evaluation_results if not r.get('correct', True) and r.get('predicted_label') is not None)
        parse_failures = sum(1 for r in evaluation_results if r.get('predicted_label') is None)

        accuracy = correct / total if total > 0 else 0.0
        precision = accuracy  # 简化计算
        recall = accuracy
        f1_score = accuracy

        return jsonify({
            'total_results': total,
            'correct_predictions': correct,
            'incorrect_predictions': incorrect,
            'parse_failures': parse_failures,
            'accuracy': round(accuracy, 3),
            'precision': round(precision, 3),
            'recall': round(recall, 3),
            'f1_score': round(f1_score, 3)
        })

    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/filters/options')
def get_filter_options():
    """获取筛选选项"""
    return jsonify(filter_options)


@app.route('/api/config/paths')
def get_config_paths():
    """获取当前配置的路径信息"""
    global excel_dir_path, results_file_path, excel_files_list
    return jsonify({
        'excel_dir_path': excel_dir_path,
        'results_file_path': results_file_path,
        'excel_files_count': len(excel_files_list) if excel_files_list else 0,
        'results_count': len(evaluation_results)
    })


@app.route('/api/data', methods=['DELETE'])
def clear_data():
    """清空数据"""
    global excel_dir_path, excel_files_list
    
    try:
        evaluation_results.clear()
        excel_dir_path = None
        excel_files_list = []
        filter_options['scenarios'] = []
        filter_options['categories'] = []

        return jsonify({'message': '数据已清空'})

    except Exception as e:
        logger.error(f"清空数据失败: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # 禁用dotenv以避免权限问题
    import os
    os.environ['FLASK_SKIP_DOTENV'] = '1'

    # 支持环境变量指定端口
    port = int(os.environ.get('PORT', 5000))

    print(f"🚀 启动Flask服务器 (端口{port})...")

    # 检测是否在沙盒环境
    try:
        # 尝试绑定端口测试
        import socket
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_socket.bind(('127.0.0.1', port))
        test_socket.close()

        # 如果能绑定，正常启动
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False
        )
    except PermissionError:
        print("⚠️  检测到沙盒环境限制，无法启动网络服务")
        print("💡 请在非沙盒环境中运行，或使用以下命令测试API：")
        print(f"   python -c \"from app import app; print('Flask应用加载成功')\"")
        print(f"   然后手动访问静态文件：file://{os.path.abspath('frontend/dist/index.html')}")
        exit(1)
    except OSError as e:
        print(f"❌ 端口绑定失败: {e}")
        print("💡 请尝试使用其他端口：PORT=8000 python app.py")
        exit(1)

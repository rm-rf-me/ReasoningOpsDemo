# app.py
import traceback
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
from threading import Lock
from reasoning.fake_api import create_all_instances, get_instance, BARuleAPI
from AlarmReasoningEnv import AlarmReasoningEnv
from functools import partial
import time
import json
import logging

logger = logging.getLogger(__name__)

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
thread = None
thread_lock = Lock()
# 全局环境实例
env = AlarmReasoningEnv()
# 全局变量记录当前处理的告警
current_alarm = None

def emit_reasoning_output(content):
    """实时发送推理过程到前端"""
    if content:
        try:
            # logger.debug(f"Emitting reasoning output at {time.strftime('%H:%M:%S')}: {content[:100]}...")
            # 添加换行符确保前端能正确解析
            socketio.emit('reasoning_update', {'content': content})
            # 确保消息立即发送
            socketio.sleep(0)
        except Exception as e:
            logger.error(f"Error emitting reasoning output: {e}", exc_info=True)

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('get_current_alarm')
def get_current_alarm():
    """获取当前正在处理的告警"""
    global current_alarm
    socketio.emit('current_alarm_update', current_alarm)
    return current_alarm

@socketio.on('next_alarm')
def next_alarm():
    """仅推进到下一条告警，不进行AI处理"""
    global current_alarm
    
    # 获取下一个未处理的告警
    alarm = env.get_next_not_processed_alarm()
    
    if not alarm:
        logger.info("No more alarms to process")
        socketio.emit('no_more_alarms', {
            'message': '所有告警已处理完成'
        })
        current_alarm = None
        return
    
    # 更新当前告警
    current_alarm = alarm
    logger.info(f"Moving to next alarm: {alarm['id']}")
    
    # 发送当前处理的告警信息
    socketio.emit('current_alarm', alarm)
    
    # 清空推理结果
    socketio.emit('clear_reasoning')
    
    # 返回所有告警的最新状态
    socketio.emit('alarms_update', {
        'all_alarms': env.get_all_alarms()
    })

@socketio.on('process_current_alarm')
def process_current_alarm(data=None):
# def process_current_alarm():
    """对当前告警进行AI推理处理"""
    global current_alarm
    # breakpoint()
    if not current_alarm:
        logger.warning("No current alarm to process")
        socketio.emit('reasoning_error', {'error': '没有当前处理的告警'})
        return
    
    logger.info(f"Processing current alarm at {time.strftime('%H:%M:%S')}: {current_alarm}")
    
    # 提取辅助信息
    auxiliary_info = {}
    if data and 'auxiliaryInfo' in data:
        auxiliary_info = data['auxiliaryInfo']
        logger.info(f"Received auxiliary info: {auxiliary_info}")
    
    def process_task():
        try:
            start_time = time.time()
            logger.info(f"Starting reasoning process at {time.strftime('%H:%M:%S')}")
            
            # 清空之前的推理结果
            socketio.emit('clear_reasoning')
            
            # 发送当前处理的告警信息
            socketio.emit('current_alarm', current_alarm)
            
            # 修改为接收新的返回值
            reasoning_result, all_reasoning_results, reasoning_history, reasoning_steps = env.process_alarm({
                "current_alarm": current_alarm,
                "history_alarms": env.get_history_alarms()
            }, output_callback=emit_reasoning_output)
            
            end_time = time.time()
            logger.info(f"Reasoning completed in {end_time - start_time:.2f} seconds")
            logger.info(f"Result: {reasoning_result}")
            
            # 更新告警状态
            env.update_alarm_state(reasoning_result)
            updated_alarms = env.get_all_alarms()
            
            socketio.emit('reasoning_complete', {
                'result': reasoning_result,
                'reasoning_text': all_reasoning_results,
                'all_alarms': updated_alarms,
                'reasoning_steps': reasoning_steps
            })
            
        except Exception as e:
            error_msg = f"Error in process_task: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            socketio.emit('reasoning_error', {'error': error_msg})

    socketio.start_background_task(process_task)

# 保留原有的process_reasoning函数作为兼容
@socketio.on('process_next_alarm')
def process_reasoning():
    """处理下一条告警的推理（兼容旧版本）"""
    next_alarm()
    process_current_alarm()

@socketio.on('connect')
def handle_connect():
    """处理客户端连接"""
    print("Client connected, initializing system...")
    
    # 初始化系统状态
    create_all_instances()
    
    # 获取告警数据并打印调试信息
    all_alarms = env.get_all_alarms()
    not_processed_alarms = env.history_windows.get_not_processed_alarms()
    
    print(f"Total alarms: {len(all_alarms)}")
    if len(all_alarms) > 0:
        print("Sample alarm data:", all_alarms[0])
    
    # 发送初始状态
    emit('init_state', {
        'all_alarms': all_alarms,
        'all_processed': env.history_windows.all_alarms,
        'not_processed_alarms': not_processed_alarms
    })
    
    # 初始化当前告警
    global current_alarm
    current_alarm = env.get_next_not_processed_alarm()
    if current_alarm:
        emit('current_alarm', current_alarm)

@socketio.on('get_ba_rules')
def get_ba_rules():
    """获取BA规则列表"""
    try:
        # 获取BA规则API实例
        ba_rule_api = get_instance(BARuleAPI)
        
        # 获取所有规则
        rules = ba_rule_api.get_all_rules()
        
        # 添加调试日志
        logger.info(f"Sending BA rules to client: {rules}")
        
        # 发送规则列表到前端
        socketio.emit('ba_rules_update', {
            'rules': rules
        })
        
    except Exception as e:
        error_msg = f"Error getting BA rules: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        socketio.emit('ba_rules_error', {'error': error_msg})

if __name__ == '__main__':
    socketio.run(app, debug=True)
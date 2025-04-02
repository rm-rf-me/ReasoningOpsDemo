# app.py
import traceback
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
from threading import Lock
from reasoning.fake_api import create_all_instances
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

@socketio.on('process_next_alarm')
def process_reasoning():
    """处理下一条告警的推理"""
    # 获取下一个未处理的告警
    alarm = env.get_next_not_processed_alarm()  # 使用 env 的方法
    logger.info(f"Processing alarm at {time.strftime('%H:%M:%S')}: {alarm}")
    
    if not alarm:
        logger.info("No more alarms to process")
        socketio.emit('reasoning_complete', {
            'result': [],
            'reasoning_text': '所有告警已处理完成',
            'all_alarms': env.get_all_alarms(),
            'reasoning_steps': []  # 添加空的推理步骤
        })
        return
        
    def process_task():
        try:
            start_time = time.time()
            logger.info(f"Starting reasoning process at {time.strftime('%H:%M:%S')}")
            
            # 发送当前处理的告警信息
            socketio.emit('current_alarm', alarm)
            
            # 修改为接收新的返回值
            reasoning_result, all_reasoning_results, reasoning_history, reasoning_steps = env.process_alarm({
                "current_alarm": alarm,
                "history_alarms": env.get_history_alarms()
            }, output_callback=emit_reasoning_output)
            
            end_time = time.time()
            logger.info(f"Reasoning completed in {end_time - start_time:.2f} seconds")
            logger.info(f"Result: {reasoning_result}")
            # logger.info(f"Reasoning steps count: {len(reasoning_steps)}")
            
            # 更新告警状态
            env.update_alarm_state(reasoning_result)
            updated_alarms = env.get_all_alarms()
            
            socketio.emit('reasoning_complete', {
                'result': reasoning_result,
                'reasoning_text': reasoning_history,  # 使用完整的推理历史
                'all_alarms': updated_alarms,
                'reasoning_steps': reasoning_steps  # 添加推理步骤
            })
            
        except Exception as e:
            error_msg = f"Error in process_task: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            socketio.emit('reasoning_error', {'error': error_msg})

    socketio.start_background_task(process_task)

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

if __name__ == '__main__':
    socketio.run(app, debug=True)
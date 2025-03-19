# app.py
import traceback
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
from threading import Lock
from reasoning.fake_api import create_all_instances
from AlarmReasoningEnv import AlarmReasoningEnv
from functools import partial
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
thread = None
thread_lock = Lock()
# 全局环境实例
env = AlarmReasoningEnv()
@app.route('/')
def index():
    return render_template('index.html')
@socketio.on('process_next_alarm')
def process_reasoning():
    """处理下一条告警的推理"""
    alarm = env.get_current_alarm()
    history_alarms = env.get_history_alarms()
    
    def process_task():
        try:
            # 收集推理过程中的输出
            reasoning_text = []
            def collect_output(content):
                if content:
                    reasoning_text.append(content)
            # 启动推理过程
            reasoning_result, all_reasoning_results = env.process_alarm({
                "current_alarm": alarm,
                "history_alarms": history_alarms
            }, output_callback=collect_output)
            
            # 更新告警状态
            env.update_alarm_state(reasoning_result)
            
            # 发送完成信号和结果
            socketio.emit('reasoning_complete', {
               'result': reasoning_result,
               'reasoning_text': ''.join(all_reasoning_results).split('现在，我们开始当前任务。')[-1],  # 将所有输出拼接成一个字符串
                'all_alarms': env.get_all_alarms(),
                'not_processed_alarms': env.history_windows.get_not_processed_alarms()
            })
        except Exception as e:
            print(f"Error in process_task: {e}, traceback: {traceback.format_exc()}")
            socketio.emit('reasoning_error', {'error': str(e)})
    socketio.start_background_task(process_task)
@socketio.on('connect')
def handle_connect():
    """处理客户端连接"""
    # 初始化系统状态
    create_all_instances()
    
    # 发送初始状态
    emit('init_state', {
        'all_alarms': env.get_all_alarms(),
        'all_processed': env.history_windows.all_alarms,
        'not_processed_alarms': env.history_windows.get_not_processed_alarms()
    })
if __name__ == '__main__':
    socketio.run(app, debug=True)
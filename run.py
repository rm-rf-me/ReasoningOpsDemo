import os
import sys
from dotenv import load_dotenv


# 加载环境变量
load_dotenv()

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from web_demo.app import app, socketio

if __name__ == '__main__':
    # 使用 eventlet 作为 WebSocket 后端
    socketio.run(app, 
                debug=True,
                host='0.0.0.0',
                port=6789,
                use_reloader=False)  # 禁用重载器避免重复初始化 
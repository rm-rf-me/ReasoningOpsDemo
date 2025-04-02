from fm.models import LLM
import json
import os
import time
import pandas as pd

class Singleton:
    _instances = {}

    @classmethod
    def get_instance(cls):
        if cls not in cls._instances:
            cls._instances[cls] = cls()
        return cls._instances[cls]

    @classmethod
    def _destroy_instance(cls):
        if cls in cls._instances:
            del cls._instances[cls]


class GraphAPI(Singleton):
    def __init__(self):
        self.graph = None

    def read_graph(self, file_path):
        # 定义 XLSX 文件路径
        xlsx_file = file_path
        # 获取所有表名
        sheet_names = pd.ExcelFile(xlsx_file, engine='openpyxl').sheet_names

        # 遍历不同 sheet 表
        for sheet_name in sheet_names:
            df = pd.read_excel(xlsx_file, sheet_name=sheet_name, engine='openpyxl')
            # 定义 CSV 文件路径，这里以 sheet 表名作为区分
            csv_file = f'{sheet_name}.csv'
            # 将数据保存为 CSV 文件
            df.to_csv(csv_file, index=False)

    def _process_graph(self):
        self.read_graph('graph_data.xlsx')
        csv_file='graph_data.csv'
        df = pd.read_csv(csv_file)

        # 将 DataFrame 转换为 JSON 数组
        self.graph = df.to_json(orient='records', force_ascii=False, indent=4)


    def query(self, description: str, max_retry: int = 3) -> str:
        llm = LLM()

        prompt = f"""
你是一个专业的暖通系统运维专家。
你需要根据描述的情况，从图结构中找出相关的设备间的拓扑关系，其中图是由二元组表示。
图结构的内容如下（JSON格式）：
{self.graph}

请根据以下描述查找相关设备间的拓扑关系：
{description}

请直接回复设备间的拓扑关系。
        """
        res = llm.query(prompt, model_name="gpt-4o")
        breakpoint()
        return res


class DeviceAPI(Singleton):
    def __init__(self):
        self.device_info = []


    def _read_device_data(self):
        """读取预设的设备信息数据"""
        fake_file = os.path.join(os.path.dirname(__file__), 'device_data.txt')
        with open(fake_file, 'r', encoding='utf-8') as f:
            # 读取所有设备并格式化为JSON结构
            device_text = f.read().strip()
            self.device_info.append(json.loads(device_text))


    def query(self, description: str, max_retry: int = 3) -> str:
        llm = LLM()

        prompt = f"""
You are a helpful assistant that can answer questions about devices.
You are given a description of a device and you need to answer the question.
All devices's information is stored in the following json format:
{self.device_info}

Please find the device information from the json and answer the question.
Description: {description}

Please answer the question in text format, or reply "No answer" if there is no answer.
        """
        res = llm.query(prompt, model_name="gpt-4o")

        return res



class BARuleAPI(Singleton):
    def __init__(self):
        self.all_rules = []
        self._read_rules()

    def _read_rules(self):
        """读取预设的运维规则数据"""
        fake_file = os.path.join(os.path.dirname(__file__), 'ba_data.txt')
        try:
            with open(fake_file, 'r', encoding='utf-8') as f:
                # 读取所有规则并格式化为JSON结构
                rules_text = f.read().strip()
                self.all_rules.append(rules_text)
        except Exception as e:
            print(f"Error reading BA rules: {e}")
            self.all_rules = []

    def query(self, description: str, max_retry: int = 3) -> str:
        llm = LLM()

        prompt = f"""
你是一个专业的暖通系统运维专家。
你需要根据描述的情况，从运维规则库中找出相关的规则内容。

运维规则库的内容如下：
{json.dumps(self.all_rules, ensure_ascii=False)}

请根据以下描述查找相关规则：
{description}

请以json格式回复你觉得有用的相关规则。
        """
        retry_delay = 1
        for retry in range(max_retry):
            try:
                res = llm.query(prompt, model_name="gpt-4o")
                # breakpoint()
                return res
            except Exception as e:
                if retry < max_retry - 1:
                    print(f"网络请求失败，重试第{retry + 1}次，延迟{retry_delay}秒: {e}")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    print(f"多次重试后仍失败: {e}")
                    return "没有找到相关规则"


class AlarmInputAPI(Singleton):
    def __init__(self):
        """初始化告警输入API"""
        self.alarm_input = []
        self.current_index = 0
        self._iterator = None
        self._read_alarm_data()

    def _read_alarm_data(self):
        """读取预设的告警数据"""
        fake_file = os.path.join(os.path.dirname(__file__), 'alarm_data.txt')
        print(f"Reading alarm data from: {fake_file}")
        
        with open(fake_file, 'r', encoding='utf-8') as f:
            # 跳过标题行
            next(f)
            for line in f:
                # 分割每一行数据
                fields = line.strip().split('\t')
                if len(fields) >= 17:  # 确保有足够的字段
                    alarm_data = {
                        'level': fields[0],                    # 告警等级
                        'alarm_msg': fields[1],                # 告警内容
                        'alarm_time': fields[2],               # 告警时间
                        'id': fields[3],                       # 告警编号
                        'location_full': fields[4],            # 告警位置全名
                        'location': fields[5],                 # 告警位置
                        'subject': fields[6],                  # 告警主体
                        'subject_short': fields[7],            # 告警主体短名称
                        'device_type': fields[8],              # 设备类型
                        'generate_type': fields[9],            # 产生类型
                        'alarm_point': fields[10],             # 告警点位
                        'alarm_rule': fields[11],              # 告警规则
                        'alarm_threshold': fields[12],         # 告警阈值
                        'alarm_value': fields[13],             # 告警值
                        'recovery_reason': fields[14],         # 恢复原因
                        'alarm_type': fields[15],              # 告警类型
                        'alarm_template': fields[16],          # 告警模板
                        'is_processed': False,                 # 处理状态
                        'is_current': False,                   # 是否为当前告警
                        'conclusion': []                       # 收敛结论
                    }
                    self.alarm_input.append(alarm_data)
        
        print(f"Loaded {len(self.alarm_input)} alarms")
        if len(self.alarm_input) > 0:
            print("Sample alarm:", self.alarm_input[0])

    def get_all_alarms(self):
        """获取所有告警"""
        alarms = self.alarm_input.copy()
        print(f"Returning {len(alarms)} alarms from API")
        if len(alarms) > 0:
            print("Sample alarm from API:", alarms[0])
        return alarms

    def wait_new(self):
        """等待新告警"""
        if not self._iterator:
            def alarm_generator():
                while self.current_index < len(self.alarm_input):
                    yield self.alarm_input[self.current_index]
                    self.current_index += 1
            
            self._iterator = alarm_generator()
        
        return self._iterator

    def reset(self):
        """重置迭代器状态"""
        self.current_index = 0
        self._iterator = None


# API管理函数
def create_all_instances():
    """创建所有API实例"""
    GraphAPI.get_instance()
    DeviceAPI.get_instance()
    BARuleAPI.get_instance()
    AlarmInputAPI.get_instance()


def destroy_all_instances():
    """销毁所有API实例"""
    GraphAPI._destroy_instance()
    DeviceAPI._destroy_instance()
    BARuleAPI._destroy_instance()
    AlarmInputAPI._destroy_instance()


def get_instance(api_class):
    """获取指定API类的实例
    
    Args:
        api_class: API类（GraphAPI、DeviceAPI等）
    
    Returns:
        对应的API实例
    """
    return api_class.get_instance()

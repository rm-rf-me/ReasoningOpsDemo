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

        请直接回复设备间的拓扑关系，如果没有找到相关设备间的拓扑关系，请回复"没有找到相关拓扑关系"。
        """
        res = llm.query(prompt, model_name="gpt-4o")


        return res


class DeviceAPI(Singleton):
    def __init__(self):
        self.device_info = []


    def _read_device_data(self):
        """读取预设的设备信息数据"""
        fake_file = os.path.join(os.path.dirname(__file__), 'ba_data.txt')
        with open(fake_file, 'r', encoding='utf-8') as f:
            # 读取所有设备并格式化为JSON结构
            device_text = f.read().strip()
            self.device_info = [{
                "device_name_Chinese":"B2区_BA_开关阀门_2号V4开关阀",
                "device_name": "B2-U2-V4",
                "content": device_text
            }]


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
                self.all_rules = [{
                    "rule_id": "R001",
                    "type": "冷冻单元故障处理",
                    "content": rules_text,
                    "keywords": ["冷冻单元", "故障", "备用", "启用"]
                }]
        except Exception as e:
            print(f"Error reading BA rules: {e}")
            self.all_rules = []

    def query(self, description: str, max_retry: int = 3) -> str:
        llm = LLM()

        prompt = f"""
        你是一个专业的暖通系统运维专家。
        你需要根据描述的情况，从运维规则库中找出相关的规则内容。
        
        运维规则库的内容如下（JSON格式）：
        {json.dumps(self.all_rules, ensure_ascii=False, indent=2)}

        请根据以下描述查找相关规则：
        {description}

        请直接回复规则内容，如果没有找到相关规则，请回复"没有找到相关规则"。
        """
        retry_delay = 1
        for retry in range(max_retry):
            try:
                res = llm.query(prompt, model_name="gpt-4o")
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
        self.alarm_input = None
        self.current_index = 0
        self._read_alarm_input()
        self._iterator = None  # 添加迭代器属性

    def _read_alarm_input(self):
        """读取预设的告警数据"""
        fake_file = os.path.join(os.path.dirname(__file__), 'alarm_data.txt')
        with open(fake_file, 'r', encoding='utf-8') as f:
            # 读取所有行并过滤空行
            self.alarm_input = [line.strip() for line in f.readlines() if line.strip()]

    def get_all_alarms(self):
        """获取所有告警"""
        return self.alarm_input.copy()

    def wait_new(self):
        """模拟告警输入的迭代器"""
        # 如果迭代器不存在，创建一个新的
        if self._iterator is None:
            if not self.alarm_input:
                self._read_alarm_input()
            
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

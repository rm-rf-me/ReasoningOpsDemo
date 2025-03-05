from fm.models import LLM
import json

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
        pass

    def _process_graph(self):
        pass

    def provide_prompt(self) -> str:
        pass

    def query(self, description: str, max_retry: int = 3) -> str:
        # 参考DeviceAPI的实现，添加基于LLM的图查询逻辑
        pass

class DeviceAPI(Singleton):
    def __init__(self):
        self.device_info = []

    def query(self, description: str, max_retry: int = 3) -> str:
        llm = LLM()

        prompt = f"""
        You are a helpful assistant that can answer questions about devices.
        You are given a description of a device and you need to answer the question.
        All devices's information is stored in the following json format:
        {self.device_info}

        Please find the device information from the json and answer the question.
        Description: {description}

        Please answer the question in the json format.
        """
        res = llm.query(prompt)

        retry = 0
        while retry < max_retry:
            try:
                res = json.loads(res)
            except Exception as e:
                retry += 1
                if retry < max_retry:
                    continue
                else:
                    raise e

        return res

class BARuleAPI(Singleton):
    def __init__(self):
        self.all_rules = []

    def query(self, description: str, max_retry: int = 3) -> str:
        llm = LLM()

        prompt = f"""
        You are a helpful assistant that can retrieve the operating rule content from the situation description.
        You are given a description of a situation and you need to retrieve the operating rule content from the situation description.
        All operating rules's information is stored in the following json format:
        {self.all_rules}

        Please find the operating rule content from the json and answer the question.
        Description: {description}

        Please answer the question in the json format.
        """
        res = llm.query(prompt)
        retry = 0
        while retry < max_retry:
            try:
                res = json.loads(res)
            except Exception as e:
                retry += 1
                if retry < max_retry:
                    continue
                else:
                    raise e

        return res

class AlarmInputAPI(Singleton):
    def __init__(self):
        self.alarm_input = None

    def wait_new(self):
        yield "Alarm Input 1"

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


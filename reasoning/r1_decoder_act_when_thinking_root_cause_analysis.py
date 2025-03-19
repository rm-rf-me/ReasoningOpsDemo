from functools import partial
from openai import OpenAI
from .utils import make_assistant, make_user
from .act_when_thinking import ActWhenThinking
from dotenv import load_dotenv
import logging
import os
import json

from .fake_api import get_instance, GraphAPI, DeviceAPI, BARuleAPI

from .prompts import root_cause_analysis_prompt

load_dotenv()


def exec_special_calc(action):
    """处理 API 调用"""
    try:
        # 解析 API 调用
        if "GraphAPI.query" in action:
            api = get_instance(GraphAPI)
            query = action.split('(')[1].strip(')"\'')
            result = api.query(query)
        elif "DeviceAPI.query" in action:
            api = get_instance(DeviceAPI)
            query = action.split('(')[1].strip(')"\'')
            result = api.query(query)
        elif "BARuleAPI.query" in action:
            api = get_instance(BARuleAPI)
            query = action.split('(')[1].strip(')"\'')
            result = api.query(query)
        else:
            raise ValueError(f"Unknown API call: {action}")
            
        return f"<result>\n{result}\n</result>\n\n"
    except Exception as e:
        return f"<result>\nError executing action: {action}, error: {e}\n</result>\n\n"


awt = ActWhenThinking(exec_special_calc)


class StreamingDecoder:

    def __rmatmul__(self, prompt):
        return self.decode(prompt)

    def __init__(self):
        self.thinking = False
        self.answer_opened = False
        self.stream = None
        self.output_callback = None
        self.client = OpenAI(
            api_key=os.environ['DEEPSEEK_API_KEY'],
            base_url=os.environ['DEEPSEEK_BASE_URL']
        )
        self.stream_creator = partial(self.client.chat.completions.create,
                                    model=os.environ['DEEPSEEK_R1_MODEL_NAME'],
                                    stream=True)
        self.stream_iterator = None
        self.continue_thinking_prompt = '''You think as above response shows. Please continue your thinking and you 
        don't have to repeat what you have done or thought before. If you think the above thinking process is enough 
        to answer the user's request, please give your answer directly instead of thinking.'''

    def create_stream(self, messages):
        """创建流式对话"""
        print("Creating stream")  # 添加日志
        self.close_stream()
        try:
            self.stream = self.stream_creator(messages=messages)
            self.stream_iterator = self.get_stream_iterator()
        except Exception as e:
            print(f"Error creating stream: {e}")  # 添加错误日志
            raise

    def close_stream(self):
        if self.stream is not None:
            self.stream.close()

    @awt.register_start_action_exec
    def wait_action(self, action):
        print("\ntake action!\n", action)
        self.close_stream()

    @awt.register_init_prompt
    @awt.register_update_prompt
    def update_prompt(self, user_prompt, thought=None):
        thought = thought or "No thought here."

        print("\nupdate prompt! restart stream\n")
        messages = [
            make_user(user_prompt),
            make_assistant(thought),
            make_user(self.continue_thinking_prompt)
        ]
        self.create_stream(messages)

    @awt.act_when_thinking
    def decode(self, prompt):
        token = next(self.stream_iterator)
        # 添加回调处理
        if self.output_callback and token:  # 只在有实际内容时发送
            self.output_callback(token)
        return token

    def get_stream_iterator(self):
        if not self.stream:
            print("Warning: No stream available")
            return None
        for completion in self.stream:
            tokens = []
            delta = completion.choices[0].delta
            if hasattr(delta, "reasoning_content"):
                reasoning_content = delta.reasoning_content
                if reasoning_content is not None:
                    if not self.thinking:
                        tokens.append("<think>\n")
                        self.thinking = True
                    tokens.append(reasoning_content)
            else:
                if self.thinking:
                    tokens.append("</think>\n\n<answer>\n")
                    self.thinking = False
                    self.answer_opened = True
                content = getattr(delta, "content", None)
                if content is not None:
                    if not self.answer_opened:
                        tokens.append("<answer>")
                        self.answer_opened = True
                    tokens.append(content)
            for token in tokens:
                if self.output_callback:
                    self.output_callback(token)
                yield token
        yield "</answer>"


def decode_main_loop(sequence: str, r1_decoder, output_callback=None) -> str:
    while True:
        try:
            token = sequence @ r1_decoder
            sequence += token
            print(token, end='')
            if output_callback:  # 在这里调用回调
                output_callback(token)
        except StopIteration:
            print("\ndecode finished!\n")
            break
    return sequence


def decode_sequence(sequence: str, output_callback=None) -> str:
    r1_decoder = StreamingDecoder()
    r1_decoder.output_callback = output_callback  # 设置回调函数
    sequence = decode_main_loop(sequence, r1_decoder, output_callback)
    return sequence


def format_prompt(alarm_info: dict) -> str:
    """
    格式化告警信息，生成推理提示
    """
    current_alarm = alarm_info["current_alarm"]
    history_alarms = alarm_info["history_alarms"]

    # 添加日志输出，检查输入数据
    print("Current alarm:", current_alarm)
    print("History alarms:", history_alarms)

    prompt = root_cause_analysis_prompt.format(
        current_alarm=current_alarm,
        history_alarms=history_alarms,
    )

    # 检查生成的提示词
    print("Generated prompt:", prompt)
    return prompt


def parse_result(result: str) -> list:
    """
    解析推理结果，返回推理结论列表
    Args:
        result: 大模型返回的推理结果字符串
    Returns:
        list: 包含推理结论的列表，每个结论是一个字典，格式如下：
        [{
            "convergence_type": "历史收敛" 或 "未来收敛",
            "related_alarm_id": "相关告警ID或None",
            "reasoning": "推理过程",
            "conclusion": "推理结论"
        }]
    """
    # 提取<answer>标签中的内容
    answer_start = result.find("<answer>") + len("<answer>")
    answer_end = result.find("</answer>")
    if answer_start == -1 or answer_end == -1:
        return []

    answer_content = result[answer_start:answer_end].strip()
    if answer_content.startswith("```json") and answer_content.endswith("```"):
        answer_content = answer_content[7:-3]
    try:
        # 解析JSON格式的结果
        conclusions = json.loads(answer_content)
        return conclusions
    except json.JSONDecodeError:
        return []


def process_alarm(alarm_info: dict, output_callback=None) -> tuple:
    """
    Args:
        alarm_info: {
            "current_alarm": str,  # 当前告警信息
            "history_alarms": list  # 历史未收敛告警列表
        }
    
    Returns:
        dict: {
            "convergence_type": str,  # "历史收敛" 或 "未来收敛"
            "related_alarms": list,  # 相关的告警ID列表
            "reasoning_process": str,  # 推理过程
            "conclusion": str  # 推理结论
        }
    """
    sequence = format_prompt(alarm_info)
    result = decode_sequence(sequence, output_callback=output_callback)

    parsered_result = parse_result(result)

    print(f"*****\n解析结果：{parsered_result}\n*****")

    return parsered_result, result


def test_openairequest():
    print("test openai request")
    client = OpenAI(
        api_key=os.environ['DEEPSEEK_API_KEY'],  # api key
        base_url=os.environ['DEEPSEEK_BASE_URL'],
    )
    print(os.environ['DEEPSEEK_API_KEY'])
    print(os.environ['DEEPSEEK_BASE_URL'])
    print(os.environ['DEEPSEEK_R1_MODEL_NAME'])
    response = client.chat.completions.create(
        model=os.environ['DEEPSEEK_R1_MODEL_NAME'],  # 通过 endpoint 指定模型 deepseek r1
        messages=[
            {
                "role": "user",
                "content": "tell me a story about a person who was injured in a car crash"
            }
        ]
    )
    print(response)


if __name__ == "__main__":
    alarm_info = {
        "current_alarm": "当前告警信息",
        "history_alarms": ["历史未收敛告警1", "历史未收敛告警2"]
    }
    process_alarm(alarm_info)

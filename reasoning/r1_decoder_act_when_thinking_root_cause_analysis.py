from functools import partial
from openai import OpenAI
from .utils import make_assistant, make_user, make_system
from .act_when_thinking import ActWhenThinking
from dotenv import load_dotenv
import logging
import os
import time
import json
from tenacity import retry, stop_after_attempt, wait_exponential
import httpx
import traceback
import re

from .fake_api import get_instance, GraphAPI, DeviceAPI, BARuleAPI

from .prompts import root_cause_analysis_prompt_mock, root_cause_analysis_prompt

load_dotenv()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def exec_special_calc(action, callback=None):
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

        res = f"<result>\n{result}\n</result>\n\n"

        if callback is not None:
            callback(res)
        return res
    except Exception as e:
        return f"<result>\nError executing action: {action}, error: {e}\n</result>\n\n"


awt = ActWhenThinking(exec_special_calc)


class StreamingDecoder:

    def __rmatmul__(self, prompt):
        return self.decode(prompt)

    def __init__(self):
        logger.info("Initializing StreamingDecoder")
        self.thinking = False
        self.answer_opened = False
        self.stream = None
        self.output_callback = None
        self.messages = None  # 添加 messages 属性
        
        # 添加记录推理历史的变量
        self.reasoning_history = ""  # 完整的推理历史文本
        self.reasoning_steps = []    # 推理步骤的JSON记录
        self.current_step = None     # 当前正在构建的步骤
        
        try:
            self.client = OpenAI(
                api_key=os.environ['DEEPSEEK_API_KEY'],
                base_url=os.environ['DEEPSEEK_BASE_URL']
            )
            logger.info("OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise
        self.stream_creator = retry(
            stop=stop_after_attempt(5),  # 增加重试次数
            wait=wait_exponential(multiplier=1, min=4, max=20),  # 调整重试等待时间
            retry=self._should_retry
        )(self.create_stream_request)
        self.stream_iterator = None
        self.continue_thinking_prompt = '''You think as above response shows. Please continue your thinking and you 
        don't have to repeat what you have done or thought before. If you think the above thinking process is enough 
        to answer the user's request, please give your answer directly instead of thinking.'''

    def set_output_callback(self, callback):
        self.output_callback = callback
        awt.set_callback_funcs(callback)

    def _should_retry(self, exception):
        """判断是否应该重试请求"""
        return isinstance(exception, (httpx.ReadError, httpx.ConnectError, ConnectionError))

    def create_stream_request(self, messages):
        """创建流式请求"""
        try:
            return self.client.chat.completions.create(
                model=os.environ['DEEPSEEK_R1_MODEL_NAME'],
                messages=messages,
                stream=True,
                temperature=0.4,
                timeout=60,  # 增加超时时间
                # headers={"Connection": "keep-alive"}  # 保持长连接
        )
        except Exception as e:
            print(f"Error creating stream request: {str(e)}")
            traceback.print_exc()
            raise

    def create_stream(self, messages):
        self.messages = messages  # 保存消息
        logger.info(f"Creating new stream with messages: {messages}")
        try:
            self.close_stream()
            self.stream = self.stream_creator(messages=messages)
            self.stream_iterator = self.get_stream_iterator()
            logger.info("Stream created successfully")
        except Exception as e:
            logger.error(f"Error creating stream: {e}")
            raise

    def close_stream(self):
        if self.stream is not None:
            self.stream.close()

    @awt.register_start_action_exec
    def wait_action(self, action):
        print("\ntake action!\n", action)
        self.close_stream()
        
        # 记录动作步骤
        if self.current_step and self.current_step['type'] == 'think':
            # 完成当前思考步骤
            self.reasoning_steps.append(self.current_step)
        
        # 创建新的动作步骤
        self.current_step = {
            'type': 'action',
            'content': action,
            'timestamp': time.time()
        }
        self.reasoning_steps.append(self.current_step)
        
        # 更新历史文本
        self.reasoning_history += f"\nAction: {action}\n"

    def record_result(self, result):
        """记录执行结果"""
        # 创建结果步骤
        result_step = {
            'type': 'result',
            'content': result,
            'timestamp': time.time()
        }
        self.reasoning_steps.append(result_step)
        
        # 更新历史文本
        self.reasoning_history += f"\nResult: {result}\n"
        
        # 重置当前步骤
        self.current_step = None

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
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                if self.stream_iterator is None:  # 确保迭代器存在
                    self.stream_iterator = self.get_stream_iterator()
                    
                token = next(self.stream_iterator)
                if token and self.output_callback:
                    self.output_callback(token)
                    
                # 更新推理历史
                if token:
                    self.reasoning_history += token
                    
                    # 处理不同类型的标记
                    if "<think>" in token and not self.current_step:
                        # 开始新的思考步骤
                        self.current_step = {
                            'type': 'think',
                            'content': token.replace("<think>", ""),
                            'timestamp': time.time()
                        }
                    elif "</think>" in token and self.current_step and self.current_step['type'] == 'think':
                        # 完成当前思考步骤
                        self.current_step['content'] += token.replace("</think>", "")
                        self.reasoning_steps.append(self.current_step)
                        self.current_step = None
                    elif "<answer>" in token:
                        # 开始答案步骤
                        if self.current_step:
                            # 完成之前的步骤
                            self.reasoning_steps.append(self.current_step)
                        
                        self.current_step = {
                            'type': 'answer',
                            'content': token.replace("<answer>", ""),
                            'timestamp': time.time()
                        }
                    elif "</answer>" in token and self.current_step and self.current_step['type'] == 'answer':
                        # 完成答案步骤
                        self.current_step['content'] += token.replace("</answer>", "")
                        self.reasoning_steps.append(self.current_step)
                        self.current_step = None
                    elif self.current_step:
                        # 继续当前步骤
                        self.current_step['content'] += token
                
                return token
                
            except StopIteration:
                logger.info("Stream iteration completed")
                # 确保最后一个步骤被添加
                if self.current_step:
                    self.reasoning_steps.append(self.current_step)
                    self.current_step = None
                return None
                
            except (httpx.ReadError, httpx.ConnectError, ConnectionError, OSError) as e:
                logger.error(f"Network error during decoding, retrying ({retry_count + 1}/{max_retries}): {e}")
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(1)
                    self.create_stream(self.messages)
                    self.stream_iterator = self.get_stream_iterator()
                else:
                    logger.error("Max retries reached during decoding.")
                    raise
                    
            except Exception as e:
                logger.error(f"Error during decoding: {e}", exc_info=True)
                raise

    def get_stream_iterator(self):
        logger.debug("Starting stream iterator")
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                if self.stream is None:  # 确保流存在
                    self.create_stream(self.messages)

                for completion in self.stream:
                    try:
                        tokens = []
                        delta = completion.choices[0].delta
                        if hasattr(delta, "reasoning_content"):
                            reasoning_content = delta.reasoning_content
                            if reasoning_content is not None:
                                if not self.thinking:
                                    tokens.append("<think>")
                                    self.thinking = True
                                tokens.append(reasoning_content)
                        else:
                            if self.thinking:
                                tokens.append("</think><answer>")
                                self.thinking = False
                                self.answer_opened = True

                            content = getattr(delta, "content", None)
                            if content is not None:
                                if not self.answer_opened:
                                    tokens.append("<answer>")
                                    self.answer_opened = True
                                tokens.append(content)
                        for token in tokens:
                            yield token
                    except Exception as e:
                        print(f"Error processing stream chunk: {str(e)}")
                        traceback.print_exc()
                        continue
                # 正常结束时，确保关闭流
                self.close_stream()
                yield "</answer>"
                break
            except (httpx.ReadError, httpx.ConnectError, ConnectionError) as e:
                logger.error(f"Network error in stream iterator, retrying ({retry_count + 1}/{max_retries}): {e}")
                retry_count += 1
                if retry_count < max_retries:
                    self.create_stream(self.messages)  # 重新创建流
            except Exception as e:
                logger.error(f"Error in stream iterator: {e}", exc_info=True)
                self.close_stream()  # 确保错误时也关闭流
                raise
        if retry_count == max_retries:
            logger.error("Max retries reached in stream iterator.")
    
    def get_reasoning_history(self):
        """获取完整的推理历史文本"""
        return self.reasoning_history
    
    def get_reasoning_steps(self):
        """获取推理步骤的JSON记录"""
        return self.reasoning_steps


def decode_main_loop(sequence, r1_decoder, output_callback=None):
    """主解码循环"""
    logger.debug("Starting decode main loop")
    try:
        while True:
            token = sequence @ r1_decoder
            if token is None:  # 流结束
                logger.debug("Decode loop completed normally")
                break
            sequence += token

            # 检查是否完成
            if sequence.endswith("</answer>"):
                logger.debug("Found end token, breaking decode loop")
                break

        return sequence

    except Exception as e:
        logger.error(f"Error in decode main loop: {e}", exc_info=True)
        raise

def decode_sequence(sequence, output_callback=None):
    """解码序列"""
    logger.info("Starting sequence decoding")
    r1_decoder = None
    try:
        r1_decoder = StreamingDecoder()
        if output_callback:
            r1_decoder.set_output_callback(output_callback)

        sequence = decode_main_loop(sequence, r1_decoder, output_callback)
        logger.info("Sequence decoding completed")

        # 解析结果
        try:
            result = parse_result(sequence)
            logger.debug(f"Parsed result: {result}")
            
            # 获取推理历史和步骤
            reasoning_history = r1_decoder.get_reasoning_history()
            reasoning_steps = r1_decoder.get_reasoning_steps()
            
            logger.debug(f"Reasoning steps: {reasoning_steps}")
            
            return result, sequence, reasoning_history, reasoning_steps
        except Exception as e:
            logger.error(f"Error parsing result: {e}", exc_info=True)
            # 如果解析失败，返回空结果和原始序列
            return [], sequence, r1_decoder.get_reasoning_history(), r1_decoder.get_reasoning_steps()

    except Exception as e:
        logger.error(f"Error in decode_sequence: {e}", exc_info=True)
        raise
    finally:
        # 确保关闭流
        if r1_decoder:
            r1_decoder.close_stream()


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


def parse_result(sequence_text):
    """解析推理结果"""
    try:
        # 提取最后一对<answer>标签中的内容
        answer_pattern = r'<answer>(.*?)</answer>'
        answer_matches = list(re.finditer(answer_pattern, sequence_text, re.DOTALL))
        
        if not answer_matches:
            logger.warning("No answer tag found in sequence")
            return []
        
        # 获取最后一个匹配结果
        last_match = answer_matches[-1]
        answer_text = last_match.group(1).strip()
        logger.debug(f"Extracted answer text from last <answer> tag: {answer_text[:100]}...")
        
        # 移除answer中可能存在的action和result标签
        answer_text = re.sub(r'<action>.*?</action>', '', answer_text, flags=re.DOTALL)
        answer_text = re.sub(r'<result>.*?</result>', '', answer_text, flags=re.DOTALL)
        
        # 尝试提取JSON部分 - 修改正则表达式以匹配带有反引号的代码块
        # 支持多种格式: ```json, ````json, `json
        json_pattern = r'[`]{3,4}(?:json)?\s*\n?(.*?)\n?[`]{3,4}'
        json_match = re.search(json_pattern, answer_text, re.DOTALL)
        
        if json_match:
            json_text = json_match.group(1).strip()
            logger.debug(f"Found JSON in code block: {json_text[:100]}...")
        else:
            # 如果没有代码块，尝试直接解析整个答案
            json_text = answer_text
            logger.debug(f"No code block found, using raw text: {json_text[:100]}...")
        
        # 清理JSON文本
        json_text = json_text.replace('None', 'null')  # 替换Python的None为JSON的null
        json_text = json_text.replace('null', 'null')  # 替换小写null
        json_text = json_text.replace('，', ',')  # 替换中文逗号
        json_text = json_text.replace('：', ':')  # 替换中文冒号
        json_text = json_text.replace('"', '"').replace('"', '"')  # 替换中文引号
        
        logger.debug(f"Cleaned JSON text: {json_text[:100]}...")
        
        try:
            # 尝试解析JSON
            result = json.loads(json_text)
            logger.info(f"Successfully parsed JSON result: {result}")
            return result
        except json.JSONDecodeError as e:
            # 如果解析失败，记录错误并尝试修复常见问题
            logger.error(f"Failed to parse JSON: {e}")
            logger.error(f"Problematic JSON text: {json_text}")
            
            # 尝试更激进的修复方法 - 添加更多日志以便调试
            try:
                logger.debug("Attempting aggressive JSON repair...")
                # 使用正则表达式提取每个对象的字段
                fixed_json = []
                object_pattern = r'{(.*?)}'
                for obj_match in re.finditer(object_pattern, json_text, re.DOTALL):
                    obj_text = obj_match.group(1).strip()
                    fixed_obj = {}
                    
                    # 提取字段
                    field_pattern = r'"([^"]+)"\s*:\s*([^,}]+)'
                    for field_match in re.finditer(field_pattern, obj_text):
                        key = field_match.group(1).strip()
                        value = field_match.group(2).strip()
                        logger.debug(f"Found field: {key} = {value}")
                        
                        # 处理值
                        if value.lower() == 'null' or value.lower() == 'none':
                            fixed_obj[key] = None
                        elif value.startswith('"') and value.endswith('"'):
                            fixed_obj[key] = value[1:-1]
                        elif value.lower() == 'true':
                            fixed_obj[key] = True
                        elif value.lower() == 'false':
                            fixed_obj[key] = False
                        else:
                            try:
                                fixed_obj[key] = int(value)
                            except ValueError:
                                try:
                                    fixed_obj[key] = float(value)
                                except ValueError:
                                    fixed_obj[key] = value
                    
                    if fixed_obj:
                        fixed_json.append(fixed_obj)
                
                if fixed_json:
                    logger.info(f"Successfully fixed JSON: {fixed_json}")
                    return fixed_json
                else:
                    logger.warning("Could not extract any valid JSON objects")
            except Exception as fix_error:
                logger.error(f"Failed to fix JSON: {fix_error}")
            
            # 如果所有修复尝试都失败，尝试最后的手动解析
            try:
                logger.debug("Attempting manual JSON parsing as last resort...")
                # 检查是否包含"未来收敛"或"历史收敛"文本
                if "未来收敛" in json_text:
                    logger.info("Detected '未来收敛' in text, creating manual result")
                    return [{
                        "convergence_type": "未来收敛",
                        "related_alarm_id": None,
                        "reasoning": "根据文本内容手动解析",
                        "conclusion": "未来相关告警可收敛至当前告警"
                    }]
                elif "历史收敛" in json_text:
                    logger.info("Detected '历史收敛' in text, creating manual result")
                    return [{
                        "convergence_type": "历史收敛",
                        "related_alarm_id": None,
                        "reasoning": "根据文本内容手动解析",
                        "conclusion": "当前告警可收敛至历史告警"
                    }]
            except Exception as manual_error:
                logger.error(f"Manual parsing failed: {manual_error}")
            
            # 如果所有尝试都失败，返回空列表
            return []
            
    except Exception as e:
        logger.error(f"Error parsing result: {e}", exc_info=True)
        return []


def process_alarm(alarm_info, output_callback=None):
    """处理告警"""
    logger.info(f"Processing alarm: {alarm_info}")
    try:
        # 构建提示词
        sequence = format_prompt(alarm_info)

        # 解码序列
        result, sequence_text, reasoning_history, reasoning_steps = decode_sequence(sequence, output_callback=output_callback)
        logger.debug(f"Decode result: {result}")
        logger.debug(f"Reasoning steps count: {len(reasoning_steps)}")

        # 如果结果为空，返回默认值
        if not result:
            result = [{
                "convergence_type": "未知",
                "related_alarm_id": None,
                "reasoning": "解析结果失败",
                "conclusion": "无法得出结论"
            }]

        # 返回结果、序列文本、推理历史和推理步骤
        # breakpoint()
        return result, sequence_text, reasoning_history, reasoning_steps

    except Exception as e:
        logger.error(f"Error processing alarm: {e}", exc_info=True)
        raise


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
        ],
        temperature=0
    )
    print(response)


if __name__ == "__main__":
    alarm_info = {
        "current_alarm": "当前告警信息",
        "history_alarms": ["历史未收敛告警1", "历史未收敛告警2"]
    }
    process_alarm(alarm_info)

from functools import partial
from openai import OpenAI
from .utils import make_assistant, make_user
from .act_when_thinking import ActWhenThinking
from dotenv import load_dotenv
import logging
import os
import time
import json
from tenacity import retry, stop_after_attempt, wait_exponential
import httpx
import traceback

from .fake_api import get_instance, GraphAPI, DeviceAPI, BARuleAPI

from .prompts import root_cause_analysis_prompt_mock

load_dotenv()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


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
        logger.info("Initializing StreamingDecoder")
        self.thinking = False
        self.answer_opened = False
        self.stream = None
        self.output_callback = None
        self.messages = None  # 添加 messages 属性
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
                temperature=0.2,
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
                return token
                
            except StopIteration:
                logger.info("Stream iteration completed")
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
            r1_decoder.output_callback = output_callback

        sequence = decode_main_loop(sequence, r1_decoder, output_callback)
        logger.info("Sequence decoding completed")

        # 解析结果
        try:
            result = parse_result(sequence)
            logger.debug(f"Parsed result: {result}")
            return result, sequence
        except Exception as e:
            logger.error(f"Error parsing result: {e}", exc_info=True)
            # 如果解析失败，返回空结果和原始序列
            return [], sequence

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

    prompt = root_cause_analysis_prompt_mock.format(
        current_alarm=current_alarm,
        history_alarms=history_alarms,
    )

    # 检查生成的提示词
    print("Generated prompt:", prompt)
    return prompt


def parse_result(result_text):
    """解析结果文本"""
    logger.debug(f"Parsing result text: {result_text}")
    try:
        # 提取 <answer> 标签中的内容
        answer_start = result_text.find("<answer>") + len("<answer>")
        answer_end = result_text.find("</answer>")
        if answer_start == -1 or answer_end == -1:
            raise ValueError("Could not find answer tags in result")
            
        answer_text = result_text[answer_start:answer_end].strip()
        logger.debug(f"Extracted answer text: {answer_text[:100]}...")

        # 处理 ```json 标记
        if answer_text.startswith("```json"):
            answer_text = answer_text[7:]  # 移除 ```json
        if answer_text.endswith("```"):
            answer_text = answer_text[:-3]  # 移除结尾的 ```

        answer_text = answer_text.strip()
        logger.debug(f"Cleaned JSON text: {answer_text[:100]}...")

        try:
            # 尝试解析 JSON
            result = json.loads(answer_text)
            logger.debug(f"Successfully parsed JSON result: {result}")
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.error(f"Problematic JSON text: {answer_text}")
            raise

    except Exception as e:
        logger.error(f"Error parsing result: {e}", exc_info=True)
        raise


def process_alarm(alarm_info, output_callback=None):
    """处理告警"""
    logger.info(f"Processing alarm: {alarm_info}")
    try:
        # 构建提示词
        sequence = format_prompt(alarm_info)

        # 解码序列
        result, sequence_text = decode_sequence(sequence, output_callback=output_callback)
        logger.debug(f"Decode result: {result}")

        # 如果结果为空，返回默认值
        if not result:
            result = [{
                "convergence_type": "未知",
                "related_alarm_id": None,
                "reasoning": "解析结果失败",
                "conclusion": "无法得出结论"
            }]

        return result, sequence_text

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

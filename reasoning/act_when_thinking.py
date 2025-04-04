from enum import Enum, auto
import random
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class DecodeState(Enum):
    BEGIN = auto()
    THINK = auto()
    ANSWER = auto()
    ACTION_BEGIN = auto()
    ACTION_END = auto()
    RESULT_START = auto()
    RESULT_END = auto()  # result end 和 begin 是等价的


def parse_generations(generations: str) -> tuple[DecodeState, Dict]:
    THINK_START = "<think>"
    THINK_END = "</think>"

    ACTION_START = "<action>"
    ACTION_END = "</action>"

    ANSWER_START = "<answer>"
    ANSWER_END = "</answer>"

    RESULT_START = "<result>"
    RESULT_END = "</result>"

    current_state = DecodeState.BEGIN
    payload = {}
    accummulated_string: str = ""
    action_string: str = ""
    for gen_char in generations:
        accummulated_string += gen_char
        if current_state == DecodeState.BEGIN:
            if accummulated_string.endswith(THINK_START):
                current_state = DecodeState.THINK

        elif current_state == DecodeState.THINK:
            if accummulated_string.endswith(ACTION_START):
                current_state = DecodeState.ACTION_BEGIN
            elif accummulated_string.endswith(ANSWER_START):
                current_state = DecodeState.ANSWER

        elif current_state == DecodeState.ANSWER:
            if accummulated_string.endswith(THINK_START):
                current_state = DecodeState.THINK
            elif accummulated_string.endswith(ANSWER_END):
                current_state = DecodeState.BEGIN
        elif current_state == DecodeState.ACTION_BEGIN:
            action_string += gen_char
            if accummulated_string.endswith(ACTION_END):
                action_string = action_string.replace(ACTION_END, "")
                payload.update({
                    "action_string": action_string
                })
                action_string = ""
                current_state = DecodeState.ACTION_END

            elif accummulated_string.endswith(ACTION_START):
                # clear action string
                action_string = accummulated_string.split(ACTION_START)[-1]

        elif current_state == DecodeState.ACTION_END:
            if accummulated_string.endswith(RESULT_START):
                current_state = DecodeState.RESULT_START

        elif current_state == DecodeState.RESULT_START:
            if accummulated_string.endswith(RESULT_END):
                user_prompt, thought = (lambda p, x: (p[:x], p[x:]) if x > 0 else (p, None))(generations,
                                                                                             generations.find(
                                                                                                 "<think>"))
                payload.update({
                    "user_prompt": user_prompt,
                    "thought": thought
                })
                current_state = DecodeState.RESULT_END

        elif current_state == DecodeState.RESULT_END:
            if not accummulated_string.endswith(RESULT_END):  # 若已经生成了下一个 token，则回归 think 态
                current_state = DecodeState.THINK

    return current_state, payload


class ActWhenThinking:
    def __init__(self, handle_action=None, callback_funcs=None):
        logger.info("Initializing ActWhenThinking")
        self.handle_action = handle_action
        self.action_handlers = []
        self.init_prompt_handlers = []
        self.update_prompt_handlers = []
        self.callback_funcs = callback_funcs

    def set_callback_funcs(self, callback_funcs):
        self.callback_funcs = callback_funcs

    def register_init_prompt(self, func):
        # 注册事件
        self.init_prompt_handlers.append(func)
        return func

    def register_update_prompt(self, func):
        # 注册事件
        self.update_prompt_handlers.append(func)
        return func

    def register_start_action_exec(self, func):
        self.action_handlers.append(func)
        return func

    def handle_action_exec(self, action):
        logger.info(f"Executing action: {action}")
        try:
            if self.callback_funcs:
                result = self.handle_action(action, self.callback_funcs)
            else:
                result = self.handle_action(action)
            logger.debug(f"Action result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error executing action: {e}", exc_info=True)
            raise

    def act_when_thinking(self, func):
        logger.debug("Registering act_when_thinking decorator")
        '''
        我们希望被装饰的函数是"不可变"的，即没有内部状态，那么状态机每次扫描都应该从头开始扫 prompt，而不是在内部保存状态字符串。
        扫描完 prompt 之后再决定下一步解码是哪一种类型。
        prompt 用于表示所有的状态。
        '''

        def wrap_func(instance, prompt, *arg, **kwargs):
            # logger.debug(f"Processing prompt in act_when_thinking: {prompt[:100]}...")
            try:
                current_state, payload = parse_generations(prompt)
                if current_state == DecodeState.BEGIN:
                    for callback in self.init_prompt_handlers:
                        callback(instance, prompt)
                    token = func(instance, prompt, *arg, **kwargs)

                elif current_state == DecodeState.THINK:
                    token = func(instance, prompt, *arg, **kwargs)

                elif current_state == DecodeState.ANSWER:
                    token = func(instance, prompt, *arg, **kwargs)

                elif current_state == DecodeState.ACTION_BEGIN:
                    token = func(instance, prompt, *arg, **kwargs)

                elif current_state == DecodeState.ACTION_END:
                    action_string: str = payload.get("action_string")
                    for callback in self.action_handlers:
                        callback(instance, action_string)
                    result = self.handle_action_exec(action_string)  # 用 action 代替 decode 获得结果
                    token = result
                elif current_state == DecodeState.RESULT_START:
                    # 这个动作应该被跳过，因为每次生成的都是完整的 <result></result>
                    pass
                elif current_state == DecodeState.RESULT_END:
                    # 回归到初始解码
                    user_prompt = payload.get("user_prompt")
                    thought = payload.get("thought")
                    for callback in self.update_prompt_handlers:
                        callback(instance, user_prompt, thought)
                    token = func(instance, prompt, *arg, **kwargs)

                return token
            except StopIteration:
                logger.debug("Stream iteration completed normally")
                return None  # 正常结束返回 None
            except Exception as e:
                logger.error(f"Error in act_when_thinking: {e}", exc_info=True)
                raise

        return wrap_func

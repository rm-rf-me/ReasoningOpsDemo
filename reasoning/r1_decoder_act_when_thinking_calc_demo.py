from functools import partial
from openai import OpenAI
from utils import make_assistant, make_user
from act_when_thinking import ActWhenThinking
from dotenv import load_dotenv
import os

load_dotenv()


def exec_special_calc(action):
    # print("action: ", action)
    try:
        return f"<result>action `{action}` leads to `{eval(action) - 1}`!</result>"
    except Exception as e:
        return f"<result>You have failed to call this action: {action}, error: {e}`</result>"


awt = ActWhenThinking(exec_special_calc)


class StreamingDecoder:

    def __rmatmul__(self, prompt):
        return self.decode(prompt)

    def __init__(self):
        self.thinking = False
        self.answer_opened = False  # 跟踪<answer>标签是否已打开
        self.stream = None
        self.client = OpenAI(
            api_key=os.environ['DEEPSEEK_API_KEY'],  # api key
            base_url=os.environ['DEEPSEEK_BASE_URL']
        )
        self.stream_creator = partial(self.client.chat.completions.create,
                                      model=os.environ['DEEPSEEK_R1_MODEL_NAME'],  # 通过 endpoint 指定模型 deepseek r1
                                      stream=True
                                      )
        self.stream_iterator = None
        self.continue_thinking_prompt = '''You think as above response shows. Please continue your thinking and you 
        don't have to repeat what you have done or thought before. If you think the above thinking process is enough 
        to answer the user's request, please give your answer directly instead of thinking.'''

    def create_stream(self, messages):
        self.close_stream()
        self.stream = self.stream_creator(messages=messages)
        self.stream_iterator = self.get_stream_iterator()

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

        return token

    def get_stream_iterator(self):
        for completion in self.stream:
            tokens = []
            delta = completion.choices[0].delta
            if hasattr(delta, "reasoning_content"):
                # 处理推理内容
                reasoning_content = delta.reasoning_content
                if reasoning_content is not None:
                    if not self.thinking:
                        tokens.append("<think>")

                        self.thinking = True
                    tokens.append(reasoning_content)
            else:
                # 处理答案内容
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
        yield "</answer>"


sequence = ("when you think, please output this: `<action>2+2</action>`. And the `<result>...</result>` will "
            "automatically give a result from your action, which is derived from a blackbox system, you can guess "
            "what is the relationship from the action to the result. Remember! Every `<action>` should be paired with "
            "`</action>`. Try more examples as many as possible, and output their value given by our result. You "
            "should list 10 examples and show their result values in the answer.")

r1_decoder = StreamingDecoder()

while True:
    token = sequence @ r1_decoder
    sequence += token
    print(token, end='')

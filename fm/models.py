from openai import OpenAI
import base64
import os
import time
import logging
from dotenv import load_dotenv

load_dotenv()


class BaseModel:
    def __init__(self):
        self.client = OpenAI(
            base_url=os.environ['FM_API_URL'],
            api_key=os.environ['FM_API_KEY']
        )

    def query(self, *args, **kwargs):
        raise NotImplementedError("Subclasses should implement this method")


class LLM(BaseModel):
    def __init__(self):
        super().__init__()

    def query(self, prompt: str, model_name: str, temperature: float = 0, timeout: int = 120,
              strict_json: bool = False, properties: dict = {}) -> str:
        # print("LLM query use model:", model_name)

        if not strict_json:
            completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model=model_name,
                timeout=timeout,
                temperature=temperature,
            )
        else:
            completion = self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format=properties,
                timeout=timeout,
                temperature=temperature
            )
        res = completion.choices[0].message.content

        return res


class VLM(BaseModel):
    def __init__(self):
        super().__init__()

    def query(self, prompt_txt: str, image_path, model_name: str = 'gpt-4o'):
        prompt = []
        image = self.get_image(image_path)
        if image is not None:
            prompt.append({
                'type': 'image_url',
                'image_url': {
                    'url': f'data:image/jpeg;base64,{image}'
                }
            })
        else:
            print('warning, no image', '*' * 50)

        prompt.insert(0, {
            'type': 'text',
            'text': prompt_txt
        })
        answer = self.retry_query_gpt(prompt, model_name)

        return answer

    def retry_query_gpt(self, prompt: str, model_name: str, retry_times=5):
        retry = 0

        completion = self.client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model=model_name,
            timeout=15
        )
        res = completion.choices[0].message.content
        return res

    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def get_image(self, image_path):
        if os.path.exists(image_path):
            return self.encode_image(image_path)
        else:
            return None


if __name__ == '__main__':
    llm = LLM()
    prompt = "What is the capital of France?"
    model_name = "gpt-4o"
    res = llm.query(prompt, model_name=model_name)
    print(res)

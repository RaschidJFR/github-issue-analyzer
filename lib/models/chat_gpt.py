from .interfaces import ConversationalLLM
from openai import OpenAI

class ChatGPT(ConversationalLLM):
  def __init__(self, api_key:str, model='gpt-4o-mini') -> None:
    self._client = OpenAI(api_key=api_key)
    self._model = model

  def prompt(self, prompt: str) -> str:
    return (
      self._client.chat.completions
        .create(messages=[{
            'role': 'user',
            'content': prompt,
          }], model=self._model)
        .choices[0].message.content)
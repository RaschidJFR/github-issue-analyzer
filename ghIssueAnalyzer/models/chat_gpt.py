from .interfaces import ConversationalLLM
from openai import OpenAI

# Use MLFlow to track the LLM usage
# See https://mlflow.org/docs/latest/genai/tracing/quickstart/
import mlflow
mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("My Application")
mlflow.openai.autolog()


class ChatGPT(ConversationalLLM):
  def __init__(self, api_key:str, model='gpt-5-mini') -> None:
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
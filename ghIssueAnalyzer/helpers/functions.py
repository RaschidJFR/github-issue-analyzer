from ..models.interfaces import ConversationalLLM
import json
import logging

def apply_prompt(issues_json: list[dict], model:ConversationalLLM, prompt: str, limit: int) -> list[dict]:
  """
  Apply a prompt to a list of github issues, calling `process_data` under the hood.

  Args:
      issues_json (list): A list of GitHub issues in JSON format.
      model (LLM): The language model to use for processing the issues.
      prompt (str): The prompt to apply to each issue.
      limit (int): (Optional) The maximum number of issues to process. Defaults to the array length.

  Returns:
      list[dict]: A list of processed issues after applying the prompt, in JSONN format.
  """
  
  
  def execute_prompt(data: str, prompt:str) -> list[dict]:
    prompt = f'{prompt}\n\nThis is the input data:\n\n{json.dumps(data)}'
    response = model.prompt(prompt)
    return json.loads(response)
  
  output = process_data(
    issues_json, 
    lambda data: execute_prompt(data, prompt), 
    limit)
  return output

  
def process_data(data: list, fn: callable, limit: int, chunk_size = 5):
  """
  Processes data in chunks and applies a given function to each chunk.

  Parameters:
  data (list): The list of data to be processed.
  fn (callable): The function to apply to each chunk of data.
  limit (int): The maximum number of elements to process.
  chunk_size (int, optional): The size of each chunk. Defaults to 10.

  Returns:
  list: The processed data.
  """
  if data is None: return []

  result = []
  total = min(len(data), limit or len(data))
  logging.debug(f'Processing {total} elements...')
  
  chunk_result = []
  try:
    for i in range(0, total, chunk_size):
      upper_index = min(i + chunk_size, total)
      logging.debug(f'Processing elements {i} to {upper_index - 1}...')
      chunk = data[i: upper_index]
      chunk_result = fn(chunk)
      result.extend(chunk_result)
      
      if len(chunk_result) < chunk_size and upper_index < total:
        logging.warning('\033[93m'
              +f'WARNING: Less elements ({len(chunk_result)}) were returned than expected ({chunk_size}). '
              + 'Try reducing chunk_size.'
              +'\033[0m')
  except Exception as e:
    logging.error(f'\033[91mError parsing response: {e}\033[0m\n\nResponse:\n{chunk_result}')
  finally:
    logging.debug(f'Finished: {len(result)} elements processed.')
  return result

def normalize_values(data: list[dict], columns: list[str]) -> list[dict]:
    column_stats = {
      col: (min(values := [item[col] for item in data if col in item]), max(values))
      for col in columns
    }
    
    result = []
    for item in data:
      normalized_item = item.copy()
      for col in columns:
        if col in normalized_item:
          min_val, max_val = column_stats[col]
          val = normalized_item[col]
          normalized_item[col] = (val - min_val) / (max_val - min_val) if max_val > min_val else 0
      result.append(normalized_item)
    
    return result
  
def merge(data1: list[dict], data2: list[dict], key: str) -> list[dict]:
  merged_data = {item[key]: item for item in data1}.copy()
  
  for item in data2.copy():
      if item[key] in merged_data:
          merged_data[item[key]].update(item)
      else:
          merged_data[item[key]] = item
          
  return list(merged_data.values())
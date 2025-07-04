from abc import ABC, abstractmethod

class ConversationalLLM(ABC):        
    @abstractmethod
    def __init__(self, api_key:str, model:str) -> None:
        pass
    
    @abstractmethod
    def prompt(self, prompt='') -> str:
        pass
    

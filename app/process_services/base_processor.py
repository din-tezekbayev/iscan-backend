from abc import ABC, abstractmethod
from typing import Dict, Any
import pandas as pd
import io

class BaseProcessor(ABC):
    @abstractmethod
    def get_prompts(self) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def process_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    def create_csv(self, results: list) -> bytes:
        if not results:
            return b""
        
        df = pd.DataFrame(results)
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        return csv_buffer.getvalue().encode('utf-8')
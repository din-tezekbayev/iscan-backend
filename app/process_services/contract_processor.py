from typing import Dict, Any, Optional
from .base_processor import BaseProcessor

class ContractProcessor(BaseProcessor):
    def __init__(self, file_type_prompts: Optional[Dict[str, Any]] = None):
        self.file_type_prompts = file_type_prompts
    
    def get_prompts(self) -> Dict[str, Any]:
        if self.file_type_prompts:
            return self.file_type_prompts
            
        return {
            "system_prompt": """You are a document processing assistant specializing in contract analysis. 
                               Extract key contract information and return it in JSON format.""",
            "extraction_prompt": """Extract the following information from this contract:
                                   - contract_title
                                   - parties (array of party names)
                                   - effective_date
                                   - expiration_date
                                   - contract_value
                                   - key_terms (array of important terms)
                                   
                                   Return the data as valid JSON.""",
            "required_fields": ["contract_title", "parties", "effective_date"]
        }
    
    def process_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        processed = result.copy()
        
        if "parties" in processed and isinstance(processed["parties"], list):
            processed["parties_count"] = len(processed["parties"])
            processed["parties_list"] = ", ".join(processed["parties"])
        
        if "contract_value" in processed:
            value_str = str(processed["contract_value"]).replace("$", "").replace(",", "")
            try:
                processed["contract_value_numeric"] = float(value_str)
            except ValueError:
                processed["contract_value_numeric"] = 0.0
        
        return processed
from typing import Dict, Any, Optional
from .base_processor import BaseProcessor

class InvoiceProcessor(BaseProcessor):
    def __init__(self, file_type_prompts: Optional[Dict[str, Any]] = None):
        self.file_type_prompts = file_type_prompts
    
    def get_prompts(self) -> Dict[str, Any]:
        if self.file_type_prompts:
            return self.file_type_prompts
            
        return {
            "system_prompt": """You are a document processing assistant specializing in invoice data extraction. 
                               Extract information accurately and return it in JSON format.""",
            "extraction_prompt": """Extract the following information from this invoice:
                                   - invoice_number
                                   - date
                                   - vendor_name
                                   - total_amount
                                   - line_items (array of {description, quantity, unit_price, total})
                                   
                                   Return the data as valid JSON.""",
            "required_fields": ["invoice_number", "vendor_name", "total_amount"]
        }
    
    def process_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        processed = result.copy()
        
        if "total_amount" in processed:
            amount_str = str(processed["total_amount"]).replace("$", "").replace(",", "")
            try:
                processed["total_amount_numeric"] = float(amount_str)
            except ValueError:
                processed["total_amount_numeric"] = 0.0
        
        if "line_items" in processed and isinstance(processed["line_items"], list):
            processed["line_items_count"] = len(processed["line_items"])
        
        return processed
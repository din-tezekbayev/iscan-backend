from typing import Dict, Any, List, Optional
from .base_processor import BaseProcessor
import re
from decimal import Decimal, InvalidOperation


class HuaweiProcessor(BaseProcessor):
    """
    Processor for Russian work completion acts (АКТ ВЫПОЛНЕННЫХ РАБОТ) from Huawei.
    Handles page-by-page processing and intelligent aggregation of P-1 forms.
    """

    def __init__(self, file_type_prompts: Optional[Dict[str, Any]] = None):
        self.file_type_prompts = file_type_prompts

    def process_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and aggregate results from multiple pages of Russian work completion acts.
        """
        if "error" in result:
            return result

        # If this is aggregated data (contains page_results), process it
        if "page_results" in result and "aggregated_data" in result:
            return self._process_aggregated_result(result)
        
        # If this is a single page result, process it normally
        return self._process_single_page_result(result)

    def _process_aggregated_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Process aggregated multi-page results"""
        processed = result.copy()
        aggregated_data = processed.get("aggregated_data", {})
        
        # Process aggregated act items
        if "act" in aggregated_data and "items" in aggregated_data["act"]:
            processed_items = []
            total_quantity = 0
            total_cost = 0
            
            for item in aggregated_data["act"]["items"]:
                processed_item = self._process_act_item(item)
                processed_items.append(processed_item)
                
                # Sum totals
                if "quantity" in processed_item:
                    try:
                        total_quantity += float(processed_item["quantity"])
                    except (ValueError, TypeError):
                        pass
                
                if "total_cost" in processed_item:
                    try:
                        cost_value = self._extract_numeric_value(processed_item["total_cost"])
                        total_cost += cost_value
                    except (ValueError, TypeError):
                        pass
            
            # Update aggregated totals
            if "totals" not in aggregated_data["act"]:
                aggregated_data["act"]["totals"] = {}
            
            aggregated_data["act"]["totals"]["total_quantity"] = total_quantity
            aggregated_data["act"]["totals"]["total_cost"] = total_cost
            aggregated_data["act"]["items"] = processed_items
        
        # Add processing statistics
        processed["processing_stats"] = {
            "pages_processed": result.get("pages_processed", 0),
            "total_act_items": len(aggregated_data.get("act", {}).get("items", [])),
            "unique_sites": len(self._extract_unique_sites(aggregated_data)),
            "unique_order_numbers": len(self._extract_unique_order_numbers(aggregated_data))
        }
        
        return processed

    def _process_single_page_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Process single page result (backward compatibility)"""
        processed = result.copy()
        
        # Process act items if present
        if "act" in processed and "items" in processed["act"]:
            processed_items = []
            for item in processed["act"]["items"]:
                processed_items.append(self._process_act_item(item))
            processed["act"]["items"] = processed_items
        
        # Extract numeric values for costs
        if "act" in processed and "totals" in processed["act"]:
            totals = processed["act"]["totals"]
            if "total_cost" in totals:
                totals["total_cost_numeric"] = self._extract_numeric_value(totals["total_cost"])
        
        return processed

    def _process_act_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual act item with numeric extraction"""
        processed_item = item.copy()
        
        # Extract numeric values from cost fields
        if "unit_price" in processed_item:
            processed_item["unit_price_numeric"] = self._extract_numeric_value(processed_item["unit_price"])
        
        if "total_cost" in processed_item:
            processed_item["total_cost_numeric"] = self._extract_numeric_value(processed_item["total_cost"])
        
        # Extract and normalize quantity
        if "quantity" in processed_item:
            try:
                processed_item["quantity_numeric"] = float(processed_item["quantity"])
            except (ValueError, TypeError):
                processed_item["quantity_numeric"] = 0.0
        
        return processed_item

    def _extract_numeric_value(self, value_str: Any) -> float:
        """Extract numeric value from string, handling Russian formatting"""
        if isinstance(value_str, (int, float)):
            return float(value_str)
        
        if not isinstance(value_str, str):
            return 0.0
        
        # Remove common currency symbols and formatting
        cleaned = str(value_str).replace("₽", "").replace("руб", "").replace("$", "")
        cleaned = cleaned.replace(",", "").replace(" ", "").strip()
        
        # Handle Russian decimal separator
        cleaned = cleaned.replace(",", ".")
        
        # Extract numeric part using regex
        numeric_match = re.search(r'[\d.]+', cleaned)
        if numeric_match:
            try:
                return float(numeric_match.group())
            except ValueError:
                pass
        
        return 0.0

    def _extract_unique_sites(self, data: Dict[str, Any]) -> List[str]:
        """Extract unique site/location names from act items"""
        sites = set()
        
        if "act" in data and "items" in data["act"]:
            for item in data["act"]["items"]:
                description = item.get("service_description", "")
                if isinstance(description, str):
                    # Look for site patterns in Russian
                    site_patterns = [
                        r'объект[:\s]+([^,\n]+)',
                        r'площадка[:\s]+([^,\n]+)',
                        r'станция[:\s]+([^,\n]+)',
                        r'узел[:\s]+([^,\n]+)'
                    ]
                    
                    for pattern in site_patterns:
                        matches = re.findall(pattern, description, re.IGNORECASE)
                        sites.update(match.strip() for match in matches)
        
        return list(sites)

    def _extract_unique_order_numbers(self, data: Dict[str, Any]) -> List[str]:
        """Extract unique order numbers from act items"""
        orders = set()
        
        if "act" in data and "items" in data["act"]:
            for item in data["act"]["items"]:
                description = item.get("service_description", "")
                if isinstance(description, str):
                    # Look for order number patterns
                    order_patterns = [
                        r'заказ[^\w]*(\d+)',
                        r'order[^\w]*(\d+)',
                        r'№[^\w]*(\d+)'
                    ]
                    
                    for pattern in order_patterns:
                        matches = re.findall(pattern, description, re.IGNORECASE)
                        orders.update(matches)
        
        return list(orders)

    def get_prompts(self) -> Dict[str, Any]:
        """Return prompts for Huawei document processing"""
        if self.file_type_prompts:
            return self.file_type_prompts
        
        return {
            "system_prompt": "You are a document processing assistant specializing in Russian work completion acts (АКТ ВЫПОЛНЕННЫХ РАБОТ) analysis. Extract key information from P-1 form telecommunications service documents and return it in structured JSON format. Pay attention to Cyrillic text, company names, addresses, contract numbers, and service details.",
            "extraction_prompt": "Extract the following information from this work completion act document: \n- document_type (form type, e.g., 'P-1') \n- document_number (if available) \n- date_of_issue (document creation/signing date) \n- customer details (name, full address, BIN/tax number) \n- contractor details (name, full address, BIN/tax number) \n- contract number and date \n- act items array containing: item number, service description (both Russian and English if available), completion date, unit of measurement, quantity, unit price, total cost \n- act totals (total quantity and total cost) \n- site/location names mentioned in service descriptions \n- order numbers referenced in descriptions. Return the data as valid JSON with proper Unicode encoding for Cyrillic characters.",
            "required_fields": ["document_type", "customer", "contractor", "contract", "act"]
        }
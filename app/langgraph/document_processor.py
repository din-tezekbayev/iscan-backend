import json
import base64
import fitz  # PyMuPDF
import io
from typing import Dict, Any, TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.config import settings

class DocumentState(TypedDict):
    file_content: bytes
    file_type_prompts: Dict[str, Any]
    processing_result: Dict[str, Any]
    page_results: List[Dict[str, Any]]
    current_page: int
    total_pages: int
    error: str

def pdf_to_images(pdf_content: bytes, max_pages: int = None) -> List[str]:
    """
    Convert PDF pages to base64 encoded PNG images.
    
    Args:
        pdf_content: PDF file content as bytes
        max_pages: Maximum number of pages to convert (default: 1)
    
    Returns:
        List of base64 encoded PNG images
    """
    try:
        # Open PDF from bytes
        pdf_document = fitz.open(stream=pdf_content, filetype="pdf")
        images = []
        
        # Convert pages to images
        pages_to_process = pdf_document.page_count if max_pages is None else min(max_pages, pdf_document.page_count)
        for page_num in range(pages_to_process):
            page = pdf_document.load_page(page_num)
            
            # Render page as PNG with high resolution
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PNG bytes
            png_data = pix.tobytes("png")
            
            # Encode as base64
            png_base64 = base64.b64encode(png_data).decode('utf-8')
            images.append(png_base64)
        
        pdf_document.close()
        return images
        
    except Exception as e:
        raise Exception(f"Failed to convert PDF to images: {str(e)}")

def parse_chatgpt_response(content: str) -> Dict[str, Any]:
    """Parse ChatGPT response and extract JSON data"""
    try:
        # First, try to parse the response directly as JSON
        return json.loads(content)
    except json.JSONDecodeError:
        # If direct parsing fails, try to extract JSON from markdown code blocks
        try:
            content = content.strip()

            # Look for JSON code blocks
            if "```json" in content:
                # Extract content between ```json and ```
                start = content.find("```json") + 7
                end = content.find("```", start)
                if end != -1:
                    json_content = content[start:end].strip()
                    return json.loads(json_content)
                else:
                    raise json.JSONDecodeError("Could not find closing ```", content, 0)
            elif "```" in content:
                # Try generic code blocks
                start = content.find("```") + 3
                end = content.find("```", start)
                if end != -1:
                    json_content = content[start:end].strip()
                    return json.loads(json_content)
                else:
                    raise json.JSONDecodeError("Could not find closing ```", content, 0)
            else:
                # Try to find JSON-like content in the response
                import re
                json_match = re.search(r'(\{.*\})', content, re.DOTALL)
                if json_match:
                    json_content = json_match.group(1)
                    return json.loads(json_content)
                else:
                    raise json.JSONDecodeError("No JSON found in response", content, 0)

        except (json.JSONDecodeError, IndexError, AttributeError):
            # If all parsing attempts fail, store raw response with error
            return {
                "raw_response": content,
                "parsing_error": "Failed to extract valid JSON from ChatGPT response"
            }

def aggregate_page_results(page_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate results from multiple pages into a single consolidated result"""
    successful_pages = [page for page in page_results if page.get("page_processing_status") == "success"]
    
    if not successful_pages:
        return {
            "error": "No pages were successfully processed",
            "page_results": page_results,
            "pages_processed": 0
        }
    
    # Initialize aggregated structure
    aggregated = {
        "pages_processed": len(successful_pages),
        "total_pages": len(page_results),
        "page_results": page_results,
        "aggregated_data": {}
    }
    
    # Find the most complete document metadata (usually from first page)
    base_data = None
    for page in successful_pages:
        if not page.get("parsing_error") and "document_type" in page:
            base_data = page
            break
    
    if not base_data and successful_pages:
        base_data = successful_pages[0]
    
    if base_data:
        # Copy basic document information
        for key in ["document_type", "document_number", "date_of_issue", "customer", "contractor", "contract"]:
            if key in base_data:
                aggregated["aggregated_data"][key] = base_data[key]
    
    # Aggregate act items from all pages
    all_act_items = []
    sites = set()
    order_numbers = set()
    
    for page in successful_pages:
        if "act" in page and isinstance(page["act"], dict):
            # Collect act items
            if "items" in page["act"] and isinstance(page["act"]["items"], list):
                for item in page["act"]["items"]:
                    if isinstance(item, dict):
                        # Add page reference to item
                        item_with_page = item.copy()
                        item_with_page["source_page"] = page.get("page_number", 0)
                        all_act_items.append(item_with_page)
                        
                        # Extract sites and order numbers
                        description = item.get("service_description", "")
                        if isinstance(description, str):
                            # Simple extraction - could be enhanced
                            import re
                            site_matches = re.findall(r'объект[:\s]+([^,\n]+)', description, re.IGNORECASE)
                            sites.update(match.strip() for match in site_matches)
                            
                            order_matches = re.findall(r'заказ[^\w]*(\d+)', description, re.IGNORECASE)
                            order_numbers.update(order_matches)
    
    # Calculate totals
    total_quantity = 0
    total_cost = 0
    
    for item in all_act_items:
        # Sum quantities
        if "quantity" in item:
            try:
                quantity = float(str(item["quantity"]).replace(",", "."))
                total_quantity += quantity
            except (ValueError, TypeError):
                pass
        
        # Sum costs
        if "total_cost" in item:
            try:
                cost_str = str(item["total_cost"]).replace("₽", "").replace("руб", "").replace(",", "").strip()
                cost_value = float(cost_str) if cost_str else 0
                total_cost += cost_value
            except (ValueError, TypeError):
                pass
    
    # Create aggregated act structure
    aggregated["aggregated_data"]["act"] = {
        "items": all_act_items,
        "totals": {
            "total_quantity": total_quantity,
            "total_cost": total_cost,
            "items_count": len(all_act_items)
        }
    }
    
    # Add extracted metadata
    aggregated["aggregated_data"]["sites"] = list(sites)
    aggregated["aggregated_data"]["order_numbers"] = list(order_numbers)
    
    # Add processing summary
    aggregated["processing_summary"] = {
        "pages_with_errors": len([p for p in page_results if p.get("page_processing_status") != "success"]),
        "pages_successfully_processed": len(successful_pages),
        "total_act_items_found": len(all_act_items),
        "unique_sites_found": len(sites),
        "unique_order_numbers_found": len(order_numbers)
    }
    
    return aggregated

def process_pdf_node(state: DocumentState) -> DocumentState:
    # Skip any extraction - just pass the PDF directly to ChatGPT
    return state

def process_with_chatgpt_node(state: DocumentState) -> DocumentState:
    if state["error"]:
        return state

    try:
        llm = ChatOpenAI(
            model="gpt-4o",
            api_key=settings.openai_api_key,
            temperature=0
        )

        system_prompt = state["file_type_prompts"].get("system_prompt", "")
        extraction_prompt = state["file_type_prompts"].get("extraction_prompt", "")

        # Convert PDF to images (all pages)
        try:
            pdf_images = pdf_to_images(state["file_content"], max_pages=None)
            
            if not pdf_images:
                raise Exception("No images generated from PDF")
        except Exception as e:
            state["error"] = f"PDF to image conversion failed: {str(e)}"
            return state

        state["total_pages"] = len(pdf_images)
        state["page_results"] = []

        # Process each page
        for page_idx, image_base64 in enumerate(pdf_images):
            state["current_page"] = page_idx + 1
            
            try:
                # Create message content with PNG image for this page
                page_prompt = f"{extraction_prompt}\n\nPage {page_idx + 1} of {len(pdf_images)}. Extract information from this specific page."
                message_content = [
                    {"type": "text", "text": page_prompt}
                ]
                
                # Add current page as image
                message_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_base64}"
                    }
                })

                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=message_content)
                ]

                response = llm.invoke(messages)
                page_result = parse_chatgpt_response(response.content)
                
                # Add page metadata
                page_result["page_number"] = page_idx + 1
                page_result["page_processing_status"] = "success"
                
                state["page_results"].append(page_result)
                
            except Exception as e:
                # Log page processing error but continue with other pages
                error_result = {
                    "page_number": page_idx + 1,
                    "page_processing_status": "failed",
                    "error": str(e)
                }
                state["page_results"].append(error_result)

        # Aggregate results from all pages
        if state["page_results"]:
            state["processing_result"] = aggregate_page_results(state["page_results"])
        else:
            state["error"] = "No pages were successfully processed"

    except Exception as e:
        state["error"] = f"ChatGPT processing failed: {str(e)}"

    return state

def validate_result_node(state: DocumentState) -> DocumentState:
    if state["error"]:
        return state

    if not state["processing_result"]:
        state["error"] = "No processing result generated"
        return state

    required_fields = state["file_type_prompts"].get("required_fields", [])

    for field in required_fields:
        if field not in state["processing_result"]:
            if "validation_errors" not in state["processing_result"]:
                state["processing_result"]["validation_errors"] = []
            state["processing_result"]["validation_errors"].append(f"Missing required field: {field}")

    return state

def create_document_processor():
    workflow = StateGraph(DocumentState)

    workflow.add_node("process_pdf", process_pdf_node)
    workflow.add_node("process_with_chatgpt", process_with_chatgpt_node)
    workflow.add_node("validate_result", validate_result_node)

    workflow.set_entry_point("process_pdf")

    workflow.add_edge("process_pdf", "process_with_chatgpt")
    workflow.add_edge("process_with_chatgpt", "validate_result")
    workflow.add_edge("validate_result", END)

    return workflow.compile()

document_processor = create_document_processor()

async def process_document(file_content: bytes, file_type_prompts: Dict[str, Any]) -> Dict[str, Any]:
    state: DocumentState = {
        "file_content": file_content,
        "file_type_prompts": file_type_prompts,
        "processing_result": {},
        "page_results": [],
        "current_page": 0,
        "total_pages": 0,
        "error": ""
    }

    final_state = await document_processor.ainvoke(state)

    if final_state["error"]:
        return {"error": final_state["error"]}

    return final_state["processing_result"]

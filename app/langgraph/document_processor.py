import json
import pymupdf
from typing import Dict, Any, List, TypedDict
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.config import settings

class DocumentState(TypedDict):
    file_content: bytes
    extracted_text: str
    file_type_prompts: Dict[str, Any]
    processing_result: Dict[str, Any]
    error: str

def extract_text_node(state: DocumentState) -> DocumentState:
    try:
        pdf_document = pymupdf.open(stream=state["file_content"], filetype="pdf")

        extracted_text = ""
        for page_num in range(pdf_document.page_count):
            page = pdf_document[page_num]
            extracted_text += page.get_text() + "\n"

        pdf_document.close()
        state["extracted_text"] = extracted_text.strip()

    except Exception as e:
        state["error"] = f"PDF extraction failed: {str(e)}"

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

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"{extraction_prompt}\n\nDocument text:\n{state['extracted_text']}")
        ]

        response = llm.invoke(messages)

        # Try to extract JSON from the response
        try:
            # First, try to parse the response directly as JSON
            result_json = json.loads(response.content)
            state["processing_result"] = result_json
        except json.JSONDecodeError:
            # If direct parsing fails, try to extract JSON from markdown code blocks
            try:
                content = response.content.strip()

                # Look for JSON code blocks
                if "```json" in content:
                    # Extract content between ```json and ```
                    start = content.find("```json") + 7
                    end = content.find("```", start)
                    if end != -1:
                        json_content = content[start:end].strip()
                        result_json = json.loads(json_content)
                        state["processing_result"] = result_json
                    else:
                        raise json.JSONDecodeError("Could not find closing ```", content, 0)
                elif "```" in content:
                    # Try generic code blocks
                    start = content.find("```") + 3
                    end = content.find("```", start)
                    if end != -1:
                        json_content = content[start:end].strip()
                        result_json = json.loads(json_content)
                        state["processing_result"] = result_json
                    else:
                        raise json.JSONDecodeError("Could not find closing ```", content, 0)
                else:
                    # Try to find JSON-like content in the response
                    import re
                    json_match = re.search(r'(\{.*\})', content, re.DOTALL)
                    if json_match:
                        json_content = json_match.group(1)
                        result_json = json.loads(json_content)
                        state["processing_result"] = result_json
                    else:
                        raise json.JSONDecodeError("No JSON found in response", content, 0)

            except (json.JSONDecodeError, IndexError, AttributeError):
                # If all parsing attempts fail, store raw response with error
                state["processing_result"] = {
                    "raw_response": response.content,
                    "parsing_error": "Failed to extract valid JSON from ChatGPT response"
                }

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

    workflow.add_node("extract_text", extract_text_node)
    workflow.add_node("process_with_chatgpt", process_with_chatgpt_node)
    workflow.add_node("validate_result", validate_result_node)

    workflow.set_entry_point("extract_text")

    workflow.add_edge("extract_text", "process_with_chatgpt")
    workflow.add_edge("process_with_chatgpt", "validate_result")
    workflow.add_edge("validate_result", END)

    return workflow.compile()

document_processor = create_document_processor()

async def process_document(file_content: bytes, file_type_prompts: Dict[str, Any]) -> Dict[str, Any]:
    state: DocumentState = {
        "file_content": file_content,
        "extracted_text": "",
        "file_type_prompts": file_type_prompts,
        "processing_result": {},
        "error": ""
    }

    final_state = await document_processor.ainvoke(state)

    if final_state["error"]:
        return {"error": final_state["error"]}

    return final_state["processing_result"]

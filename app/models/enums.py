from enum import Enum


class ProcessingMode(str, Enum):
    """Processing mode for document analysis"""
    IMAGE_OCR = "IMAGE_OCR"  # Convert PDF to images and send to ChatGPT for OCR-style processing
    TEXT_EXTRACTION = "TEXT_EXTRACTION"  # Extract text from PDF and send to ChatGPT


class ProcessorType(str, Enum):
    """Type of processor to use for document processing"""
    HUAWEI_ACT = "HUAWEI_ACT"  # Russian work completion acts from Huawei
    INVOICE = "INVOICE"  # General invoice processing
    CONTRACT = "CONTRACT"  # Contract document processing
    RECEIPT = "RECEIPT"  # Receipt processing
    CUSTOM = "CUSTOM"  # Custom processor
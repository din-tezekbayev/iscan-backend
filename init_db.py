from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.models import Base, FileType

Base.metadata.create_all(bind=engine)

def init_db():
    db: Session = SessionLocal()
    
    # Check if file types already exist
    existing_types = db.query(FileType).count()
    if existing_types > 0:
        print("Database already initialized")
        return
    
    # Create default file types
    default_file_types = [
        {
            "name": "invoice",
            "description": "Invoice documents for automated data extraction",
            "processing_prompts": {
                "system_prompt": "You are a document processing assistant specializing in invoice data extraction. Extract information accurately and return it in JSON format.",
                "extraction_prompt": "Extract the following information from this invoice: - invoice_number - date - vendor_name - total_amount - line_items (array of {description, quantity, unit_price, total}). Return the data as valid JSON.",
                "required_fields": ["invoice_number", "vendor_name", "total_amount"]
            }
        },
        {
            "name": "contract",
            "description": "Contract documents for key information extraction",
            "processing_prompts": {
                "system_prompt": "You are a document processing assistant specializing in contract analysis. Extract key contract information and return it in JSON format.",
                "extraction_prompt": "Extract the following information from this contract: - contract_title - parties (array of party names) - effective_date - expiration_date - contract_value - key_terms (array of important terms). Return the data as valid JSON.",
                "required_fields": ["contract_title", "parties", "effective_date"]
            }
        },
        {
            "name": "receipt",
            "description": "Receipt documents for expense tracking",
            "processing_prompts": {
                "system_prompt": "You are a document processing assistant specializing in receipt data extraction. Extract information accurately and return it in JSON format.",
                "extraction_prompt": "Extract the following information from this receipt: - merchant_name - date - total_amount - tax_amount - items (array of {description, price}). Return the data as valid JSON.",
                "required_fields": ["merchant_name", "date", "total_amount"]
            }
        }
    ]
    
    for file_type_data in default_file_types:
        file_type = FileType(**file_type_data)
        db.add(file_type)
    
    db.commit()
    print(f"Initialized database with {len(default_file_types)} file types")
    db.close()

if __name__ == "__main__":
    init_db()
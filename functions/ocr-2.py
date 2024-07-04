import os
import json
import fitz
import azure
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from msrest.authentication import CognitiveServicesCredentials
from io import BytesIO
import time
import logging
import sys
from classify import process_pdf, filter_pages, excluded_types

def getcreds():
    user = os.getenv('CREDS_USER')
    password = os.getenv('CREDS_PASSWORD')
    
    if not user or not password:
        raise ValueError("Credentials not set in environment variables")
    
    return user, password

class DocClient:
    def __init__(self, endpoint, key):
        self.client = ComputerVisionClient(endpoint, CognitiveServicesCredentials(key))
    
    def close(self):
        self.client.close()
    
    def extract_content(self, result):
        contents = {}
        for read_result in result.analyze_result.read_results:
            lines = read_result.lines
            lines.sort(key=lambda line: line.bounding_box[1])
            page_content = []
            for line in lines:
                page_content.append(" ".join([word.text for word in line.words]))
            contents[f"page_{read_result.page}"] = "\n".join(page_content)
        return contents
    
    def pdf2df(self, pdf_path, classification_json):
        all_pages_content = []
        doc = fitz.open(pdf_path)
        num_pages = doc.page_count
        for i in range(num_pages):
            if classification_json['messages'][i]['type'] in excluded_types:
                all_pages_content.append({f"page_{i+1}": ""})
                continue
            
            try:
                page = doc.load_page(i)
                pix = page.get_pixmap(dpi=300)
                img_byte_arr = BytesIO(pix.tobytes(output="png"))
                ocr_result = self.client.read_in_stream(img_byte_arr, raw=True)
                operation_id = ocr_result.headers["Operation-Location"].split("/")[-1]
                while True:
                    result = self.client.get_read_result(operation_id)
                    if result.status.lower() not in ["notstarted", "running"]:
                        break
                    time.sleep(1)
                if result.status.lower() == "failed":
                    logging.error(f"OCR failed for page {i+1} of file {pdf_path}")
                    continue
                page_results = self.extract_content(result)
                all_pages_content.append(page_results)
            except azure.core.exceptions.HttpResponseError as e:
                logging.error(f"Error processing page {i+1} of file {pdf_path}: {e}")
                continue
        return all_pages_content
    
    def process(self, pdf_path, classification_json):
        return self.pdf2df(pdf_path, classification_json)

def reformat_json_structure(data):
    new_messages = []
    for page_data in data:
        for key, content in page_data.items():
            new_messages.append({
                "page_content": content,
                "page_number": 0  # Placeholder value, will be updated later
            })
    return {"messages": new_messages}

def update_page_numbers(data):
    messages = data["messages"]
    for i, message in enumerate(messages, start=1):
        message["page_number"] = i
    return data

if __name__ == "__main__":
    logger = logging.getLogger()
    azurelogger = logging.getLogger("azure")
    logger.setLevel(logging.INFO)
    azurelogger.setLevel(logging.ERROR)
    
    if len(sys.argv) != 3:
        logger.error("Usage: python ocr.py <path_to_pdf_file> <path_to_output_file>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_path = sys.argv[2]
    
    if not pdf_path.lower().endswith('.pdf'):
        logger.error(f"File {pdf_path} is not a PDF")
        sys.exit(1)
    
    classification_json = process_pdf(pdf_path)
    
    endpoint, key = getcreds()
    client = DocClient(endpoint, key)
    
    results = client.process(pdf_path, classification_json)
    formatted_results = reformat_json_structure(results)
    filtered_results = filter_pages(classification_json, formatted_results, excluded_types)
    updated_results = update_page_numbers(filtered_results)
    
    with open(output_path, "w") as output_file:
        json.dump(updated_results, output_file, indent=4)
    
    client.close()
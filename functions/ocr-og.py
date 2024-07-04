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

    def pdf2df(self, pdf_path):
        all_pages_content = []
        doc = fitz.open(pdf_path)
        num_pages = doc.page_count
        for i in range(num_pages):
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

    def image2df(self, image_path):
        all_pages_content = []
        try:
            with open(image_path, "rb") as img_file:
                img_byte_arr = img_file.read()
                ocr_result = self.client.read_in_stream(BytesIO(img_byte_arr), raw=True)
                operation_id = ocr_result.headers["Operation-Location"].split("/")[-1]
                while True:
                    result = self.client.get_read_result(operation_id)
                    if result.status.lower() not in ["notstarted", "running"]:
                        break
                    time.sleep(1)
                if result.status.lower() == "failed":
                    logging.error(f"OCR failed for image file {image_path}")
                    return all_pages_content
                page_results = self.extract_content(result)
                all_pages_content.append(page_results)
        except azure.core.exceptions.HttpResponseError as e:
            logging.error(f"Error processing image file {image_path}: {e}")
        return all_pages_content

    def process(self, file_path):
        if file_path.lower().endswith('.pdf'):
            return self.pdf2df(file_path)
        elif file_path.lower().endswith(('.jpeg', '.jpg', '.png')):
            return self.image2df(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_path}")

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
        logger.error("Usage: python ocr.py <path_to_file> <path_to_output_file>")
        sys.exit(1)

    file_path = sys.argv[1]
    output_path = sys.argv[2]

    if not file_path.lower().endswith(('.pdf', '.jpeg', '.jpg', '.png')):
        logger.error(f"File {file_path} is not a supported format")
        sys.exit(1)

    endpoint, key = getcreds()
    client = DocClient(endpoint, key)

    results = client.process(file_path)
    formatted_results = reformat_json_structure(results)
    updated_results = update_page_numbers(formatted_results)

    with open(output_path, "w") as output_file:
        json.dump(updated_results, output_file, indent=4)

    client.close()

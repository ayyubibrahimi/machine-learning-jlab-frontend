import os
import json
import fitz  # PyMuPDF
import azure
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from msrest.authentication import CognitiveServicesCredentials
from io import BytesIO
import time
import logging
import sys
import easyocr
import numpy as np
import cv2
from concurrent.futures import ThreadPoolExecutor, as_completed

def getcreds():
    user = os.getenv('CREDS_USER')
    password = os.getenv('CREDS_PASSWORD')
    
    if not user or not password:
        raise ValueError("Credentials not set in environment variables")
    
    return user, password

class DocClient:
    def __init__(self, endpoint, key):
        self.client = ComputerVisionClient(endpoint, CognitiveServicesCredentials(key))
        self.easyocr_reader = easyocr.Reader(['en'], gpu=False, detect_network='craft', recog_network='english_g2')

    def close(self):
        self.client.close()

    def extract_content_azure(self, result):
        contents = {}
        for read_result in result.analyze_result.read_results:
            lines = read_result.lines
            lines.sort(key=lambda line: line.bounding_box[1])
            page_content = []
            for line in lines:
                page_content.append(" ".join([word.text for word in line.words]))
            contents[f"page_{read_result.page}"] = "\n".join(page_content)
        return contents

    def advanced_preprocess_image(self, img):
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img
        
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        contrast = clahe.apply(gray)
        
        binary = cv2.adaptiveThreshold(contrast, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        
        denoised = cv2.fastNlMeansDenoising(binary, None, 10, 7, 21)
        
        kernel = np.ones((1,1), np.uint8)
        dilated = cv2.dilate(denoised, kernel, iterations=1)
        
        eroded = cv2.erode(dilated, kernel, iterations=1)
        
        return eroded

    def process_with_easyocr(self, image_data):
        result = self.easyocr_reader.readtext(image_data)
        sorted_result = sorted(result, key=lambda x: x[0][0][1])  # Sort by top-left y-coordinate
        return "\n".join([text for _, text, _ in sorted_result])

    def process_page(self, page, page_num):
        try:
            pix = page.get_pixmap(dpi=300)
            img_byte_arr = BytesIO(pix.tobytes(output="png"))
            
            # Try Azure OCR first
            try:
                ocr_result = self.client.read_in_stream(img_byte_arr, raw=True)
                operation_id = ocr_result.headers["Operation-Location"].split("/")[-1]
                while True:
                    result = self.client.get_read_result(operation_id)
                    if result.status.lower() not in ["notstarted", "running"]:
                        break
                    time.sleep(1)
                if result.status.lower() == "failed":
                    raise azure.core.exceptions.HttpResponseError("Azure OCR failed")
                page_results = self.extract_content_azure(result)
            except azure.core.exceptions.HttpResponseError as e:
                logging.warning(f"Azure OCR failed for page {page_num}, falling back to EasyOCR: {str(e)}")
                # Fallback to EasyOCR
                img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                processed_img = self.advanced_preprocess_image(img)
                page_content = self.process_with_easyocr(processed_img)
                page_results = {f"page_{page_num}": page_content}
            
            return page_results
        except Exception as e:
            logging.error(f"Error processing page {page_num}: {str(e)}")
            return {f"page_{page_num}": ""}

    def pdf2df(self, pdf_path):
        doc = fitz.open(pdf_path)
        with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            future_to_page = {executor.submit(self.process_page, page, i+1): i+1 for i, page in enumerate(doc)}
            all_pages_content = []
            for future in as_completed(future_to_page):
                page_num = future_to_page[future]
                try:
                    page_results = future.result()
                    all_pages_content.append(page_results)
                except Exception as e:
                    logging.error(f"Error processing page {page_num} of file {pdf_path}: {str(e)}")
        
        all_pages_content.sort(key=lambda x: int(list(x.keys())[0].split('_')[1]))
        return all_pages_content

    def image2df(self, image_path):
        all_pages_content = []
        try:
            with open(image_path, "rb") as img_file:
                img_byte_arr = img_file.read()
                
                # Try Azure OCR first
                try:
                    ocr_result = self.client.read_in_stream(BytesIO(img_byte_arr), raw=True)
                    operation_id = ocr_result.headers["Operation-Location"].split("/")[-1]
                    while True:
                        result = self.client.get_read_result(operation_id)
                        if result.status.lower() not in ["notstarted", "running"]:
                            break
                        time.sleep(1)
                    if result.status.lower() == "failed":
                        raise azure.core.exceptions.HttpResponseError("Azure OCR failed")
                    page_results = self.extract_content_azure(result)
                except azure.core.exceptions.HttpResponseError as e:
                    logging.warning(f"Azure OCR failed for image, falling back to EasyOCR: {str(e)}")
                    # Fallback to EasyOCR
                    img = cv2.imdecode(np.frombuffer(img_byte_arr, np.uint8), cv2.IMREAD_COLOR)
                    processed_img = self.advanced_preprocess_image(img)
                    page_content = self.process_with_easyocr(processed_img)
                    page_results = {"page_1": page_content}
                
                all_pages_content.append(page_results)
        except Exception as e:
            logging.error(f"Error processing image file {image_path}: {str(e)}")
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
import os
import json
import logging
import subprocess
import tempfile
from uuid import uuid4
from flask import request, jsonify
import firebase_admin
from firebase_admin import credentials, storage, firestore
import functions_framework
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from create_pdf_and_email import create_pdf


# Initialize Firebase Admin SDK if not already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate('FirebaseConfig.json')
    firebase_admin.initialize_app(cred, {
        'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET')
    })

firestore_client = firestore.client()
bucket = storage.bucket()

logging.info(f"Using Firebase storage bucket: {bucket.name}")

def process_file(file, temp_dir, batch_directory, unique_file_id, selected_script, selected_model, custom_template):
    logging.info(f"Processing file: {file.filename}")

    temp_file_path = os.path.join(temp_dir, f'{unique_file_id}_{file.filename}')
    file.save(temp_file_path)
    logging.info(f"Saved uploaded file to temporary path: {temp_file_path}")

    temp_output_path = os.path.join(batch_directory, f'{unique_file_id}_{file.filename}.json')
    logging.info(f"OCR output will be stored at: {temp_output_path}")

    ocr_script_path = os.path.join(os.getcwd(), 'ocr.py')
    logging.info(f"Running OCR script: {ocr_script_path} with args: {temp_file_path}, {temp_output_path}")
    ocr_result = subprocess.run(['python3', ocr_script_path, temp_file_path, temp_output_path], capture_output=True)

    if ocr_result.returncode != 0:
        logging.error(f"OCR script error: {ocr_result.stderr.decode('utf-8')}")
        return None, None, None

    logging.info(f"OCR script completed successfully")
    logging.info(f"OCR output stored at: {temp_output_path}")

    process_output_path = os.path.join(temp_dir, f'{unique_file_id}_processed_output.json')
    logging.info(f"Processed output will be stored at: {process_output_path}")

    if selected_script in ['process-detailed.py', 'process-brief.py', 'process-comprehensive.py', 'timelines.py']:
        process_script_path = os.path.join(os.getcwd(), selected_script)
        logging.info(f"Running process script: {process_script_path} with args: {batch_directory}, {selected_model}, {custom_template}, {process_output_path}")
        process_result = subprocess.run(
            ['python3', process_script_path, batch_directory, selected_model, custom_template, process_output_path],
            capture_output=True
        )

        if process_result.returncode != 0:
            logging.error(f"Process script error: {process_result.stderr.decode('utf-8')}")
            return None, None, None

        logging.info(f"Process script completed successfully")
        logging.info(f"Processed output stored at: {process_output_path}")

    return temp_file_path, temp_output_path, process_output_path

def upload_files(file, unique_file_id, temp_file_path, temp_output_path, process_output_path, pdf_summary_path):
    pdf_blob = bucket.blob(f'uploads/{unique_file_id}_{file.filename}.pdf')
    json_blob = bucket.blob(f'ocr_output/{unique_file_id}_{file.filename}.json')
    processed_blob = bucket.blob(f'processed_output/{unique_file_id}_{file.filename}.json')
    pdf_summary_blob = bucket.blob(f'pdf_summaries/{unique_file_id}_summary.pdf')

    logging.info(f"Uploading PDF file to: {pdf_blob.name}")
    pdf_blob.upload_from_filename(temp_file_path)
    logging.info(f"Uploading JSON file to: {json_blob.name}")
    json_blob.upload_from_filename(temp_output_path)
    logging.info(f"Uploading processed file to: {processed_blob.name}")
    processed_blob.upload_from_filename(process_output_path)
    logging.info(f"Uploading PDF summary to: {pdf_summary_blob.name}")
    pdf_summary_blob.upload_from_filename(pdf_summary_path)

    expiration_time = timedelta(days=365)
    pdf_file_url = pdf_blob.generate_signed_url(expiration=expiration_time)
    json_file_url = json_blob.generate_signed_url(expiration=expiration_time)
    processed_file_url = processed_blob.generate_signed_url(expiration=expiration_time)
    pdf_summary_url = pdf_summary_blob.generate_signed_url(expiration=expiration_time)

    return pdf_file_url, json_file_url, processed_file_url, pdf_summary_url

def send_email(recipient_email, pdf_summary_url):
    sender_email = os.environ.get('SENDER_EMAIL')
    sender_password = os.environ.get('SENDER_PASSWORD')

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = "Your Processed Document Summary"

    body = f"Please find your document summary at the following link: {pdf_summary_url}\n\nThis link will expire in 1 day."
    msg.attach(MIMEText(body, 'plain'))

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)


def store_in_firestore(unique_id, file, pdf_file_url, json_file_url, processed_file_url, pdf_summary_url, processed_data):
    logging.info(f"Adding entry to Firestore for file: {file.filename}")
    firestore_client.collection('uploads').add({
        'id': unique_id,
        'filename': file.filename,
        'pdfFileUrl': pdf_file_url,
        'jsonFileUrl': json_file_url,
        'processedFileUrl': processed_file_url,
        'pdfSummaryUrl': pdf_summary_url,  # Add this line
        'processedData': processed_data,
        'uploadedAt': firestore.SERVER_TIMESTAMP
    })

def handle_file(file, selected_script, selected_model, custom_template, send_email_flag, user_email):
    with tempfile.TemporaryDirectory() as temp_dir:
        logging.info(f"Created temporary directory: {temp_dir}")

        unique_file_id = str(uuid4())
        batch_directory = os.path.join(temp_dir, f'batch_{unique_file_id}')
        os.makedirs(batch_directory, exist_ok=True)
        logging.info(f"Created batch directory: {batch_directory}")

        temp_file_path, temp_output_path, process_output_path = process_file(
            file, temp_dir, batch_directory, unique_file_id, selected_script, selected_model, custom_template
        )

        if temp_file_path and temp_output_path and process_output_path:
            pdf_summary_path = os.path.join(temp_dir, f'{unique_file_id}_summary.pdf')
            create_pdf(process_output_path, pdf_summary_path)

            pdf_file_url, json_file_url, processed_file_url, pdf_summary_url = upload_files(
                file, unique_file_id, temp_file_path, temp_output_path, process_output_path, pdf_summary_path
            )

            with open(process_output_path, 'r') as f:
                processed_data = f.read()
            processed_results = json.loads(processed_data)
            logging.info(f'Processed Results: {processed_results}')

            store_in_firestore(unique_file_id, file, pdf_file_url, json_file_url, processed_file_url, pdf_summary_url, processed_data)

            if send_email_flag == 'true' and user_email:
                try:
                    send_email(user_email, pdf_summary_url)
                    logging.info(f"Email sent to {user_email}")
                except Exception as e:
                    logging.error(f"Error sending email: {str(e)}")

            return {
                'filename': file.filename,
                'pdfFileUrl': pdf_file_url,
                'jsonFileUrl': json_file_url,
                'processedFileUrl': processed_file_url,
                'processedData': processed_data,
                'pdfSummaryUrl': pdf_summary_url
            }
        else:
            logging.error(f"Error processing file: {file.filename}")
            return None

@functions_framework.http
def uploadFunction(request):
    logging.info(f"Received request: {request}")

    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, PUT, POST, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return '', 204, headers

    headers = {'Access-Control-Allow-Origin': '*'}
    if 'files' not in request.files:
        logging.error("No files uploaded")
        return jsonify({"error": "No files uploaded"}), 400, headers

    files = request.files.getlist('files')
    selected_script = request.form.get('script')
    selected_model = request.form.get('model')
    custom_template = request.form.get('custom_template')
    send_email_flag = request.form.get('send_email')
    user_email = request.form.get('user_email')

    if not files or not selected_script or not selected_model or not custom_template:
        logging.error(f"Missing parameters. Files: {files}, Script: {selected_script}, Model: {selected_model}, Custom Template: {custom_template}")
        return jsonify({"error": "Missing parameters"}), 400, headers

    uploaded_files = []
    unique_id = str(uuid4())

    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(handle_file, file, selected_script, selected_model, custom_template, send_email_flag, user_email) for file in files]
        for future in as_completed(futures):
            result = future.result()
            if result:
                uploaded_files.append(result)

    logging.info(f"Uploaded files: {uploaded_files}")
    return jsonify({"uniqueId": unique_id, "results": uploaded_files}), 200, headers
import json
import logging
import re
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

def create_pdf(processed_data_path, pdf_path):
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    logging.info(f"Attempting to read JSON data from: {processed_data_path}")

    try:
        with open(processed_data_path, 'r') as file:
            processed_data = json.load(file)

        logging.info(f"Successfully loaded JSON data. Number of items: {len(processed_data)}")

        for item in processed_data:
            if item['files']:
                # Strip the unique ID and .json extension from the filename
                original_filename = item['files'][0]['filename']
                cleaned_filename = re.sub(r'^[a-f0-9-]+_', '', original_filename)
                cleaned_filename = cleaned_filename.rsplit('.json', 1)[0]
                
                story.append(Paragraph(f"Document: {cleaned_filename}", styles['Heading1']))
                story.append(Spacer(1, 12))

            for file_data in item['files']:
                # Add page interval for each file_data
                start_page = file_data.get('start_page', 'N/A')
                end_page = file_data.get('end_page', 'N/A')
                story.append(Paragraph(f"Pages: {start_page} - {end_page}", styles['Heading2']))
                story.append(Spacer(1, 6))

                sentences = file_data['sentence'].split('\n')
                in_bullet_list = False
                
                for sentence in sentences:
                    if sentence.strip().startswith('-'):
                        if not in_bullet_list:
                            in_bullet_list = True
                            story.append(Spacer(1, 6))
                        story.append(Paragraph(sentence, styles['Normal']))
                    else:
                        if in_bullet_list:
                            in_bullet_list = False
                            story.append(Spacer(1, 6))
                        story.append(Paragraph(sentence, styles['Normal']))
                        story.append(Spacer(1, 6))

                # Add a spacer after each file_data summary
                story.append(Spacer(1, 12))

        doc.build(story)
        logging.info(f"PDF created successfully at: {pdf_path}")

    except json.JSONDecodeError as e:
        logging.error(f"JSON decoding error: {str(e)}")
        with open(processed_data_path, 'r') as file:
            logging.error(f"Content causing the error: {file.read()[:500]}...")
    except IOError as e:
        logging.error(f"IO error when trying to read the file: {str(e)}")
    except Exception as e:
        logging.error(f"Unexpected error in create_pdf: {str(e)}")
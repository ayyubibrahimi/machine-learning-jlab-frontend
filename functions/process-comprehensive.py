import os
import logging
import json
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
from collections import namedtuple
import re

Doc = namedtuple("Doc", ["page_content", "metadata"])

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

def get_api_key():
    api_key = os.getenv('API_KEY')
    if not api_key:
        raise ValueError("API key not set in environment variables")
    return api_key

api_key = get_api_key()

llm = ChatAnthropic(model_name="claude-3-haiku-20240307", api_key=api_key, temperature=0)


def load_and_split(file_path):
    logger.info(f"Processing document: {file_path}")

    with open(file_path, "r") as file:
        file_content = file.read()
        try:
            data = json.loads(file_content)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            data = {}

    print(f"Keys in parsed JSON data: {data.keys()}")

    if "messages" in data:
        if data["messages"]:
            docs = []
            for message in data["messages"]:
                doc = Doc(
                    page_content=message["page_content"],
                    metadata={"seq_num": message["page_number"]},
                )
                docs.append(doc)
            print(docs)

            logger.info(f"Data loaded from document: {file_path}")
            return docs


summary_template = """
As a Legal Clerk, your task is to generate a comprehensive, bulletpoint summary of all the important information contained in the provided document excerpt. Extract all the key details presented in the current page. Follow these guidelines to create an accurate and thorough summary:

## Guidelines ##

{custom_template}

2. Present the summary in a bullet point format, using subheadings if needed to organize distinct aspects of the information.

3. DO NOT include any details not explicitly stated in any of the documents. If no details are present, state that there are no details.

### IMPORTANT ###
    
DO NOT INCLUDE ANYD DETAILS NOT EXPLICITLY STATED. IF NO DETAILS ARE PRESENT, STATE THAT THERE ARE NO DETAILS. 

### Documents To Review ###

## Current Page ##:

{current_page}

### Current Page Summary:
"""

improvement_template = """
    As a Legal Clerk, your task is to review and improve the generated summary of a legal document page. You will be provided with the raw page content and the initially generated summary. Your goal is to create an improved summary that captures all important information accurately and presents it in a clear, bullet-point format.

    ## Guidelines:

    1. {custom_template}

    2. Review the raw page content and the initial summary carefully.
    3. Ensure all important information from the raw page is included in the summary.
    4. Ensure that the summary is accurate and not misleading.
    
    
    Header 1:
    - Detail 1
    - Detail 2
    
    Header 2:
    - Detail 1
    - Detail 2


    7. Present the information in a clear, concise bullet-point format.
    6. Use the following format for your summary:
        
        Header 1:
        - Detail 1
        - Detail 2
        
        Header 2:
        - Detail 1
        - Detail 2

    ### IMPORTANT ###
    
    DO NOT INCLUDE ANYD DETAILS NOT EXPLICITLY STATED. IF NO DETAILS ARE PRESENT, STATE THAT THERE ARE NO DETAILS. 

    ### Documents To Review ###
    Raw Page Content:
    {raw_page}

    Initial Summary:
    {initial_summary}

    Please provide an improved summary below, addressing any missing information, inaccuracies, or formatting errors:

    Improved Summary:
    """

def process_page(docs, custom_template, i):
    prompt_response = ChatPromptTemplate.from_template(summary_template)
    response_chain = prompt_response | llm | StrOutputParser()

    improvement_prompt = ChatPromptTemplate.from_template(improvement_template)
    improvement_chain = improvement_prompt | llm | StrOutputParser()

    current_page = docs[i].page_content.replace("\n", " ")
    page_number = docs[i].metadata.get("seq_num")

    processed_content = response_chain.invoke(
        {
            "custom_template": custom_template,
            "current_page": current_page,
        }
    )

    improved_summary = improvement_chain.invoke(
        {   
            "custom_template": custom_template,
            "raw_page": current_page,
            "initial_summary": processed_content,
        }
    )

    print(f"Processed Content: {processed_content}")

    return {"page_content": improved_summary, "page_number": page_number}


def generate_summaries(docs, custom_template):
    summaries = []

    with ThreadPoolExecutor() as executor:
        future_to_page = {executor.submit(process_page, docs, custom_template, i): i for i in range(len(docs))}
        
        for future in as_completed(future_to_page):
            page_index = future_to_page[future]
            try:
                result = future.result()
                summaries.append(result)
            except Exception as exc:
                print(f'Page {page_index} generated an exception: {exc}')
        
    summaries.sort(key=lambda x: x["page_number"])
    return summaries

def clean_summary(summary):
    # Remove any introductory text followed by a colon
    cleaned_summary = re.sub(r'^[^:]+:\s*', '', summary.strip())
    
    # Split the summary into lines
    summary_lines = cleaned_summary.split('\n')
    
    # Remove any empty lines at the beginning
    while summary_lines and not summary_lines[0].strip():
        summary_lines.pop(0)
    
    # Join the lines back together
    return '\n'.join(summary_lines).strip()


def save_summaries_to_json(summaries, output_file):
    output_data = []
    for summary in summaries:
        cleaned_summary = clean_summary(summary["page_content"])
        output_data.append(
            {
                "sentence": cleaned_summary,
                "filename": os.path.basename(output_file),
                "start_page": summary["page_number"],
                "end_page": summary["page_number"],
            }
        )

    return {"files": output_data}

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(
            "Please provide the path to the directory, the selected model, and the output path as command-line arguments."
        )
        sys.exit(1)

    input_directory = sys.argv[1]
    selected_model = sys.argv[2]
    custom_template = sys.argv[3]
    output_path = sys.argv[4]
    output_data = []

    custom_template = str(custom_template)


    try:
        for entry in os.listdir(input_directory):
            entry_path = os.path.join(input_directory, entry)

            if os.path.isfile(entry_path) and entry.endswith(".json"):
                # Process individual JSON file
                docs = load_and_split(entry_path)
                query = "Generate a timeline of events based on the police report."
                combined_summaries = generate_summaries(docs, custom_template)
                output_data.append(save_summaries_to_json(combined_summaries, entry))

            elif os.path.isdir(entry_path):
                # Process directory containing JSON files
                for filename in os.listdir(entry_path):
                    if filename.endswith(".json"):
                        input_file_path = os.path.join(entry_path, filename)

                        docs = load_and_split(
                            input_file_path
                        )  # Changed from entry_path to input_file_path
                        combined_summaries = generate_summaries(docs, custom_template)
                        output_data.append(
                            save_summaries_to_json(combined_summaries, filename)
                        )

        # Convert the output data to JSON string
        with open(output_path, "w") as output_file:
            json.dump(output_data, output_file, indent=4)

    except Exception as e:
        logger.error(f"Error processing JSON: {str(e)}")
        print(json.dumps({"success": False, "message": "Failed to process JSON"}))
        sys.exit(1)

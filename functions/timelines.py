import os
import logging
import json
from langchain_core.prompts import ChatPromptTemplate
from nltk.corpus import stopwords
from langchain_anthropic import ChatAnthropic
from concurrent.futures import ThreadPoolExecutor, as_completed


from langchain.output_parsers import PydanticOutputParser
from typing import List, Any
from dateutil import parser
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import json
import os
import sys

from pydantic import BaseModel, Field, ValidationError, root_validator
from collections import namedtuple
Doc = namedtuple("Doc", ["page_content", "metadata"])


logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)

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



class Person(BaseModel):
    name: str = Field(description="Name of the person associated with the event")

class Event(BaseModel):
    description: str = Field(description="Description of the event")
    date: str = Field(description="Date of the event")
    # persons: List[Person] = Field(description="Persons associated with the event")

class EventSummary(BaseModel):
    events: List[Event] = Field(description="List of events extracted from the page")

    @root_validator(pre=True)
    def validate_events(cls, values):
        events = values.get('events', [])
        if not isinstance(events, list):
            raise ValueError("Events must be a list")

        validated_events = []
        for event in events:
            if isinstance(event, dict) and 'description' in event and 'date' in event:
                validated_events.append(event)
            else:
                # If event is invalid, append a default empty event
                validated_events.append(Event(description="", date="").dict())

        values['events'] = validated_events
        return values


event_summary_parser = PydanticOutputParser(pydantic_object=EventSummary)


summary_template = """
As a Legal Clerk, your task is to follow the guidelines below from the judge. 

### Guidelines from the Judge ###

1. Identify each date on the page. Extract all information related to the event associated with that date. 

All events must meet the following criteria:
- At least one date and one event must be in the string.  
- Describe the entire event associated with the date.
- If multiple events occur on the same date, list them as separate bullet points.

Here is an example of what the output should look like:
{format_instructions}

2. Do not include or infer any details not explicitly stated in the current page.

3. All quotation marks must be removed. Only provide raw text.  

4. If there are no events. Return an empty string.  

### IMPORTANT: FORMAT INSTRUCTIONS ###
Format your response as an object that conforms to the following schema:

{format_instructions}

1. Format the date as YYYY-MM-DD


### Page Extract Events From: Current Page: ###

{current_page}

Return:
"""


def process_page(docs, i):
    prompt_response = ChatPromptTemplate.from_template(summary_template)
    response_chain = prompt_response | llm | event_summary_parser

    current_page = docs[i].page_content.replace("\n", " ").strip()
    page_number = docs[i].metadata.get("seq_num")
    format_instructions = event_summary_parser.get_format_instructions()

    if current_page:
        processed_content = response_chain.invoke(
            {
                "current_page": current_page,
                "format_instructions": format_instructions,
            }
        )
        return {"page_number": page_number, "summary": processed_content}
    else:
        return {"page_number": page_number, "summary": None}


def generate_summaries(docs):
    combined_summaries = []
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(process_page, docs, i): i for i in range(len(docs))}
        
        for future in as_completed(futures):
            try:
                result = future.result()
                if result is not None and result["summary"] is not None:
                    combined_summaries.append(result)
            except Exception as exc:
                logger.error(f'Generated an exception: {exc}')
        
        combined_summaries.sort(key=lambda x: x["page_number"])
    return combined_summaries

def standardize_date(date_str):
    if date_str.lower() in ["n/a", "unknown"]:
        return date_str.capitalize()
    
    try:
        parsed_date = parser.parse(date_str, fuzzy=True)
        return parsed_date.strftime("%Y-%m-%d")
    except ValueError:
        return date_str

class EventDeduplicate(BaseModel):
    description: str = Field(description="Description of the event")
    page: str = Field(description="Page number where the event is mentioned")
    # persons: List[Person] = Field(description="Persons associated with the event")


class EventDeduplicateSummary(BaseModel):
    events: List[EventDeduplicate] = Field(description="List of deduplicated events")

    @root_validator(pre=True)
    def validate_events(cls, values):
        events = values.get('events', [])
        if not isinstance(events, list):
            raise ValueError("Events must be a list")

        validated_events = []
        for event in events:
            if isinstance(event, dict) and 'description' in event and 'page' in event:
                validated_events.append(event)
            else:
                # If event is invalid, append a default empty event
                validated_events.append(EventDeduplicate(description="", page="").dict())

        values['events'] = validated_events
        return values


event_deduplicate_parser = PydanticOutputParser(pydantic_object=EventDeduplicateSummary)

deduplicate_template = """
As a Legal Clerk, your task is to follow the guidelines below: 

1. This is a list of events that occurred on the same day. Re-write the text so that events that seem to be duplicates are grouped as one event. If the events occurred on different pages, list each page number. 

Format your response as a JSON object that conforms to the following schema:

{format_instructions}

Events
{event}
"""

def deduplicate_events(event_text: str) -> EventDeduplicateSummary:
    prompt_response = PromptTemplate(template=deduplicate_template, input_variables=["event", "format_instructions"])
    response_chain = prompt_response | llm | event_deduplicate_parser

    format_instructions = event_deduplicate_parser.get_format_instructions()

    processed_content = response_chain.invoke({
        "event": event_text,
        "format_instructions": format_instructions
    })

    # processed_content should already be validated by the event_deduplicate_parser
    return processed_content

def save_timeline_to_json(timeline_data, filename):
    output_data = []
    for event in timeline_data:
        output_data.append({
            "sentence": event["sentence"],
            "page_numbers": event["page_numbers"],
            "filename": filename
        })

    return {"files": output_data}

def process_sorted_timeline(summaries, filename):
    logging.info(f"Processing sorted timeline for file: {filename}")
    events_by_date = {}
    output_data = []

    for summary in summaries:
        for event in summary["summary"].events:
            standardized_date = standardize_date(event.date)
            if standardized_date not in events_by_date:
                events_by_date[standardized_date] = []
            events_by_date[standardized_date].append({
                "Page": summary["page_number"],
                "Event Description": event.description,
                # "Persons Associated with the Event": [person.name for person in event.persons],
            })

    sorted_dates = sorted(events_by_date.keys())
    logging.info(f"Sorted dates: {sorted_dates}")

    for date in sorted_dates:
        logging.info(f"Processing events for date: {date}")
        current_event_text = ""
        for event in events_by_date[date]:
            current_event_text += f"- Page: {event['Page']}\n"
            current_event_text += f"- Event Description: {event['Event Description']}\n"
            # current_event_text += "- Persons Associated with the Event:\n"
            # for person in event["Persons Associated with the Event"]:
            #     current_event_text += f"  - {person}\n"
            current_event_text += "\n"

        try:
            logging.info(f"Current event text: {current_event_text}")
            deduplicated_event_summary = deduplicate_events(current_event_text)
            logging.info(f"deduplicated_event_summary: {deduplicated_event_summary}")
            for event in deduplicated_event_summary.events:
                logging.info(f"event: {event}")
                sentence = f"Date: {date}\n{event.description}"
                output_data.append({
                    "sentence": sentence,
                    "page_numbers": event.page.split(','),
                    "filename": filename
                })
        except ValidationError as e:
            logging.error(f"Validation error for events on {date}: {str(e)}")
        except Exception as e:
            if "Invalid json output" in str(e):
                logging.warning(f"Ignored error: {str(e)}")
            else:
                logging.error(f"An unexpected error occurred: {str(e)}")
                sys.exit(1)

    logging.info(f"Processed sorted timeline for file: {filename}")
    return save_timeline_to_json(output_data, filename)


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Please provide the input directory, selected model, custom template, and output path as command-line arguments.")
        sys.exit(1)

    input_directory = sys.argv[1]
    selected_model = sys.argv[2]
    custom_template = sys.argv[3]
    output_path = sys.argv[4]
    output_data = []

    logging.info(f"Input directory: {input_directory}")
    logging.info(f"Selected model: {selected_model}")
    logging.info(f"Custom template: {custom_template}")
    logging.info(f"Output path: {output_path}")

    try:
        for entry in os.listdir(input_directory):
            entry_path = os.path.join(input_directory, entry)

            if os.path.isfile(entry_path) and entry.endswith(".json"):
                logging.info(f"Processing file: {entry_path}")
                docs = load_and_split(entry_path)
                combined_summaries = generate_summaries(docs)
                json_output = process_sorted_timeline(combined_summaries, os.path.basename(entry_path))
                output_data.append(json_output)

            elif os.path.isdir(entry_path):
                for filename in os.listdir(entry_path):
                    if filename.endswith(".json"):
                        input_file_path = os.path.join(entry_path, filename)
                        logging.info(f"Processing file in directory: {input_file_path}")
                        docs = load_and_split(input_file_path)
                        combined_summaries = generate_summaries(docs)
                        json_output = process_sorted_timeline(combined_summaries, os.path.basename(input_file_path))
                        output_data.append(json_output)

        with open(output_path, "w") as output_file:
            json.dump(output_data, output_file, indent=4)
        logging.info(f"Successfully wrote output to {output_path}")

    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
        sys.exit(1)
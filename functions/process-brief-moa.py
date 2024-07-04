import os
import logging
import json
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
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

llm_1 = ChatAnthropic(model_name="claude-3-haiku-20240307", api_key=api_key, temperature=0)

llm_2 = ChatAnthropic(model_name="claude-3-haiku-20240307", api_key=api_key, temperature=0)

llm_3 = ChatAnthropic(model_name="claude-3-haiku-20240307", api_key=api_key, temperature=0)

llm_4 = ChatAnthropic(model_name="claude-3-haiku-20240307", api_key=api_key, temperature=0)

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
                page_content = message.get("page_content", "")
                if page_content:  # Only append if page_content is not an empty string
                    doc = Doc(
                        page_content=page_content,
                        metadata={"seq_num": message.get("page_number")}
                    )
                    docs.append(doc)
            # print(docs)

            logger.info(f"Data loaded from document: {file_path}")
            return docs


memory_log_template = """
As a Legal Clerk, update the memory log only when the new summary contains crucial information directly related to the main subject of the document. Maintain a concise memory log that focuses on the key aspects of the events, allegations, investigations, and outcomes described in the document.

## Guidelines ##

1. Review the current memory log and new summary to determine if an update is necessary.

2. If the new summary contains crucial information specific to the main subject of the document, identify the key details to include.

3. ONLY INCLUDE INFORMATION ABOUT THE FOLLOWING KEY DETAILS:
   - The specific allegations, charges, or rule violations
   - Key events and actions during any investigations
   - Important evidence or findings
   - Legal proceedings, motions, or resolutions
   - Disciplinary actions or outcome

4. DO NOT infer any details that are not explicitly stated in the source document. Only return information contained within the document. You can do this by returning the exact language and phrases used. 

5. Reproduce the updated memory log or the original memory log, if it does not need to be updated with information from the new summary. 

IMPORTANT
Provide your response in a format similar to the examples below. Limit the memory log to these categories:

**Example**:
Incident Overview:

Details of Alleged Misconduct:

Investigation Findings:

Recommended Disciplinary Action:

## Original Memory Log ##: {memory_log}

## New Summary ##: {summary}

## Original Memory Log or Updated Memory Log ##:
"""

memory_log_verification_template = """
As a Legal Clerk, compare the old memory log with the updated memory log to ensure that no important information specific to the main subject of the document has been accidentally deleted in the update process. The memory log should serve as a concise summary of the key aspects of the events, allegations, investigations, and outcomes described in the document.

Guidelines:
1. Carefully review both the old and updated memory logs.

2. Identify any crucial information present in the old memory log that is missing from the updated memory log, focusing on details directly related to the main subject of the document.

3. Reproduce the updated memory log if it does not need to be updated with information from the original memory log. 

4. DO NOT infer any details that are not explicitly stated in the source document. Only return information contained within the document. You can do this by returning the exact language and phrases used. 

## Original Memory Log ##: {old_memory_log}

## Updated Memory Log ##: {updated_memory_log}

## Updated Memory Log or New Memory Log##:
"""

def update_memory_log(memory_log, new_summary):
    memory_log_prompt = ChatPromptTemplate.from_template(memory_log_template)
    memory_log_chain = memory_log_prompt | llm | StrOutputParser()
    updated_memory_log = memory_log_chain.invoke({"summary": new_summary, "memory_log": memory_log})
    memory_log_verification_prompt = ChatPromptTemplate.from_template(memory_log_verification_template)
    memory_log_verification_chain = memory_log_verification_prompt | llm | StrOutputParser()
    final_memory_log = memory_log_verification_chain.invoke({"old_memory_log": memory_log, "updated_memory_log": updated_memory_log})
    return final_memory_log

def create_memory_log(docs, pages_to_concatenate=2):
    memory_log = ""
    num_pages = len(docs)
    
    # Helper function to concatenate specified number of pages
    def concatenate_pages(start_idx, num_pages_to_concat):
        combined_content = ""
        for j in range(num_pages_to_concat):
            if start_idx + j < num_pages:
                combined_content += docs[start_idx + j].page_content.replace("\n", " ") + " "
        return combined_content.strip()
    
    # Process the first pages based on the concatenation length
    for i in range(0, min(10, num_pages), pages_to_concatenate):
        combined_content = concatenate_pages(i, pages_to_concatenate)
        summary = process_memory_log_page(docs, i, combined_content, 0, memory_log)["page_content"]
        memory_log = update_memory_log(memory_log, summary)
        print(f"ORIGINAL MEMORY LOG {memory_log}")
    
    # Process the last pages (skipping the first ones if already processed)
    start_index = max(10, num_pages - 10)
    for i in range(start_index, num_pages, pages_to_concatenate):
        combined_content = concatenate_pages(i, pages_to_concatenate)
        summary = process_memory_log_page(docs, i, combined_content, 0, memory_log)["page_content"]
        memory_log = update_memory_log(memory_log, summary)
        # print(f"UPDATED MEMORY LOG {memory_log}")
    
    return memory_log

def process_memory_log_page(docs, i, current_page, window_size, memory_log):
    prompt_response = ChatPromptTemplate.from_template(summary_template)
    response_chain = prompt_response | llm | StrOutputParser()

    previous_page_ending = (
        docs[i - 1].page_content.replace("\n", " ")[-window_size:]
        if i > 0
        else ""
    )
    next_page_beginning = (
        docs[i + 1].page_content.replace("\n", " ")[:window_size]
        if i < len(docs) - 1
        else ""
    )
    page_number = docs[i].metadata.get("seq_num")
    response = {"page_content": "", "page_number": page_number}
    if current_page:
        processed_content = response_chain.invoke(
            {
                "memory_log": memory_log,
                "previous_page_ending": previous_page_ending,
                "current_page": current_page,
                "next_page_beginning": next_page_beginning,
            }
        )
        response["page_content"] = processed_content

    return response

summary_template = """
As a Legal Clerk, your task is to generate a comprehensive, bulletpoint summary of all the important information contained in the provided document excerpt. You will be given three sections of text: Previous Page Ending, Next Page Beginning, and Current Page. Your main focus should be on the Current Page, using the other sections for context when necessary.

## Critical Instructions ##
1. NEVER include any information about "John Doe" or "Jane Doe" in your summary.
2. If there is no relevant content to summarize in the Current Page, return an empty string ("").
3. DO NOT infer, assume, or hallucinate any information not explicitly stated in the provided text.
4. Treat this task as a binary classification: either there is relevant information to summarize, or there isn't.

## Guidelines ##
1. Focus primarily on the content under the "Current Page" heading.
2. Extract only explicitly stated important details from the current page, including but not limited to:
   - Individuals mentioned (except John/Jane Doe), including their full names, roles, badge numbers, and specific actions
   - Allegations, charges, and/or rule violations, providing case numbers and exact dates when available
   - Main events, actions, and/or observations described, including precise dates and locations when provided
   - Relevant evidence or findings presented
   - Legal proceedings, motions, disciplinary actions, or investigation outcomes, including specific dates, case law citations, and arguments made by involved parties
3. Use the "Previous Page Ending" and "Next Page Beginning" sections only to provide context or clarify information from the current page when necessary.
4. Present the summary in a bullet point format, using subheadings if needed to organize distinct aspects of the information.

### Documents To Review ###
Carefully read and analyze the content under each of the following headings:

## Previous Page Ending ##
{previous_page_ending}

## Next Page Beginning ##
{next_page_beginning}

## Current Page ##
{current_page}

Based on the content provided under these headings, particularly focusing on the Current Page, provide a comprehensive summary following the guidelines. If there is no relevant information to summarize, return an empty string (""):

### Current Page Summary:
"""

aggregation_template = """
You are tasked with aggregating and synthesizing the summaries produced by three different language models. Your goal is to create a comprehensive, accurate, and coherent summary that incorporates the best elements from each model's output.

## Critical Instructions ##
1. NEVER include any information about "John Doe" or "Jane Doe" in your aggregated summary.
2. If all three model summaries are empty or contain no relevant information, return an empty string ("").
3. DO NOT infer, assume, or hallucinate any information not explicitly stated in the provided summaries.
4. Treat this task as a binary classification: either there is relevant information to aggregate, or there isn't.

## Guidelines ##
1. Analyze the three summaries for consistency and complementary information.
2. Identify and prioritize the most important and relevant points from each summary.
3. Combine the information to create a unified, non-redundant summary.
4. Ensure that all key details, including names (except John/Jane Doe), dates, events, and legal information, are accurately represented.
5. Maintain the bullet-point format for clarity and readability.
6. If there are conflicting pieces of information, include both with a note about the discrepancy.

## Model 1 Summary ##
{summary_1}

## Model 2 Summary ##
{summary_2}

## Model 3 Summary ##
{summary_3}

Based on the summaries provided above, provide an aggregated summary following the guidelines. If there is no relevant information to aggregate, return an empty string (""):

### Aggregated Summary:
"""
def process_page(docs, i, query, window_size, memory_log, pages_per_chunk):
    prompt_response = ChatPromptTemplate.from_template(summary_template)
    
    # Create chains for each LLM
    response_chain_1 = prompt_response | llm_1 | StrOutputParser()
    response_chain_2 = prompt_response | llm_2 | StrOutputParser()
    response_chain_3 = prompt_response | llm_3 | StrOutputParser()
    
    current_pages = []
    page_numbers = []
    for j in range(pages_per_chunk):
        if i + j < len(docs):
            current_page = docs[i + j].page_content.replace("\n", " ")
            current_pages.append(current_page)
            page_number = docs[i + j].metadata.get("seq_num")
            page_numbers.append(page_number)
    
    previous_page_ending = (
        docs[i - 1].page_content.replace("\n", " ")[-window_size:]
        if i > 0
        else ""
    )
    next_page_beginning = (
        docs[i + pages_per_chunk].page_content.replace("\n", " ")[:window_size]
        if i + pages_per_chunk < len(docs)
        else ""
    )
    
    response = {"page_content": "", "page_numbers": page_numbers}
    
    if current_pages:
        # Generate summaries from each LLM
        input_data = {
            "previous_page_ending": previous_page_ending,
            "current_page": " ".join(current_pages),
            "next_page_beginning": next_page_beginning,
        }
        
        summary_1 = response_chain_1.invoke(input_data)
        summary_2 = response_chain_2.invoke(input_data)
        summary_3 = response_chain_3.invoke(input_data)

        print(f"Summary 1 Response: {summary_1}")

        print(f"Summary 2 Response: {summary_2}")
        
        print(f"Summary 3 Response: {summary_3}")
        
        # Aggregate the summaries using llm_4
        aggregation_prompt = ChatPromptTemplate.from_template(aggregation_template)
        aggregation_chain = aggregation_prompt | llm_4 | StrOutputParser()
        
        aggregated_summary = aggregation_chain.invoke({
            "summary_1": summary_1,
            "summary_2": summary_2,
            "summary_3": summary_3
        })
        
        print(f"Aggregated Summary: {aggregated_summary}")
        response["page_content"] = aggregated_summary
    
    return response


combine_template = """
As a Legal Clerk, your task is to concatenate the provided page summaries into a single, comprehensive, and well-organized summary for the given section of the document. This summary should present all relevant information from both the current combined summary and the new page summary in a detailed, chronological, and coherent manner without any duplication. 

## Guidelines ##:

1. Comprehensive Information Integration:
   - Review the current combined summary and the new page summary to extract the most important information that is relevant to producing a summary. 
   - Include full names, roles, badge numbers, specific events with dates, policy or rule violations, disciplinary actions, relevant evidence, legal actions, and outcomes related to the case from both sources.

3. Narrative Coherence:
    Support the extracted data with additional context from the memory log and surrounding pages to enhances the understanding or relevance of the information in the current page. The memory log should be used to help you understand what is relevant and what is irrelevant. 
    
4. Handling Contradictions:
   - If inconsistencies arise between the current combined summary and the new page summary, prioritize the most detailed and specific information. If the information is incomplete, do not include it. 

5. Factual Accuracy:
   - DO NOT include any details not explicitly stated in either summary.

6. Formatting for Clarity:
   - Ensure that the updated combined summary is formatted as bullet points with a logical flow of information. If possible, organize the bullet points chronologically. 
   
IMPORTANT
Provide your response in a format similar to the examples below:

**Example**:
Incident Overview:
- Brief description of the incident, including date, location, and involved parties
- Overview of the alleged misconduct and the department's response

Details of Alleged Misconduct:
- How and when the alleged misconduct was discovered
- Details about the evidence that led to the discovery
- Specific policy violation or rule violation

Officer's Statement and Context:
- Officer's admission or denial of the allegations
- Any contextual information provided by the officer to explain their actions

Witness Statements:
- Relevant information provided by witnesses, if applicable
- How witness statements support or contradict the officer's account

Investigation Findings:
- Summary of the investigation's findings
- Specific violations of department policies or regulations
- Disciplinary action

Complaint and Recommended Disciplinary Action:
- Details about the formal complaint filed against the officer
- Recommended disciplinary actions based on the investigation's findings

Case Status:
- Current status of the case and any pending actions
- Brief summary of the key points and conclusion of the report

Summaries:

## Current Combined Summary ##:
{current_combined_summary}

## New Page Summary ##:
{new_page_summary}

## Updated Combined Summary: ##
"""


verification_template = """
As a Legal Clerk, your task is to review the updated combined summary, which integrates content from the current combined summary and the new summary of a document. This verification process aims to ensure that all relevant information from both the current combined summary and the new summary is accurately retained in the updated combined summary, such as full names, roles, badge numbers, specific events with dates, policy or rule violations, disciplinary actions, relevant evidence, legal actions, and outcomes related to the case from both sources.

## Verification Guidelines ##

1. Comprehensive Information Integration:
   - Ensure that all important details from the new summary, such as critical people, key facts, key events, and significant details, are accurately incorporated into the updated combined summary.

2. Context Preservation:
   - Verify that all of the important information from both the current combined summary and the new summary is preserved in the updated combined summary.
   
3. Logical Flow:
   - Evaluate the updated combined summary for logical flow and coherence, ensuring that the newly integrated information fits seamlessly into the existing narrative. If possible, this information should be ordered chronologically. 
   
4. Factual Accuracy:
   - DO NOT include any details not explicitly stated in either summary.

   
IMPORTANT
Do not change the formatting style of the updated combined summary.
Follow the exact format as specified below.

Focus solely on integrating and verifying the content from the provided summaries.

## Current Combined Summary ##:
{current_combined_summary}

## New Summary ##:
{new_page_summary}

## Provide the updated combined summary below, ensuring that all relevant information from both the current combined summary and the new summary is accurately retained. If no updates are needed, return the current combined summary ##
"""



def combine_summaries(summaries, memory_log):
    combiner_llm_1 = llm_1
    combiner_llm_2 = llm_2
    combiner_llm_3 = llm_3
    aggregator_llm = llm_4
    verification_llm = llm_1

    combiner_prompt = ChatPromptTemplate.from_template(combine_template)
    aggregator_prompt = ChatPromptTemplate.from_template(aggregation_template)
    verification_prompt = ChatPromptTemplate.from_template(verification_template)

    combiner_chain_1 = combiner_prompt | combiner_llm_1 | StrOutputParser()
    combiner_chain_2 = combiner_prompt | combiner_llm_2 | StrOutputParser()
    combiner_chain_3 = combiner_prompt | combiner_llm_3 | StrOutputParser()
    aggregator_chain = aggregator_prompt | aggregator_llm | StrOutputParser()
    verification_chain = verification_prompt | verification_llm | StrOutputParser()

    combined_summaries = []

    for section_summaries in summaries:
        current_combined_summary = section_summaries["messages"][0]["page_content"]
        combined_page_numbers = section_summaries["messages"][0].get(
            "page_numbers", [section_summaries["messages"][0].get("page_number")]
        )

        for i in range(1, len(section_summaries["messages"])):
            new_page_summary = section_summaries["messages"][i]["page_content"]

            # Generate summaries using three different models
            summary_1 = combiner_chain_1.invoke({
                "current_combined_summary": current_combined_summary,
                "new_page_summary": new_page_summary,
            })
            summary_2 = combiner_chain_2.invoke({
                "current_combined_summary": current_combined_summary,
                "new_page_summary": new_page_summary,
            })
            summary_3 = combiner_chain_3.invoke({
                "current_combined_summary": current_combined_summary,
                "new_page_summary": new_page_summary,
            })

            # Aggregate the summaries
            aggregated_summary = aggregator_chain.invoke({
                "summary_1": summary_1,
                "summary_2": summary_2,
                "summary_3": summary_3
            })

            # Verify the aggregated summary
            verified_combined_summary = verification_chain.invoke({
                "updated_combined_summary": aggregated_summary,
                "current_combined_summary": current_combined_summary,
                "new_page_summary": new_page_summary,
            })

            print(f"VERIFIED COMBINED SUMMARY: {verified_combined_summary}")

            current_combined_summary = verified_combined_summary

            combined_page_numbers.extend(
                section_summaries["messages"][i].get("page_numbers", [section_summaries["messages"][i].get("page_number")])
            )

        improved_summary, improved_memory_log = format_and_improve_summary(current_combined_summary, summaries, memory_log)

        combined_summaries.append({"page_content": improved_summary, "page_numbers": combined_page_numbers})

    return combined_summaries, memory_log


def process_batch(batch_docs, batch_start, query, window_size, memory_log, pages_per_chunk):
    sorted_results = []
    for i in range(0, len(batch_docs), pages_per_chunk):
        result = process_page(batch_docs, i, query, window_size, memory_log, pages_per_chunk)
        sorted_results.append(result)

    section_summaries = {"messages": sorted_results}
    combined_summaries, _ = combine_summaries([section_summaries], memory_log)
    start_page = sorted_results[0]["page_numbers"][0]
    end_page = sorted_results[-1]["page_numbers"][-1]
    
    return combined_summaries[0], start_page, end_page


def generate_summaries(docs, query, memory_log, window_size=100, batch_size=20, pages_per_chunk=10):
    batches = [docs[i:i+batch_size] for i in range(0, len(docs), batch_size)]
    combined_summaries = []

    with ThreadPoolExecutor() as executor:
        future_to_batch = {executor.submit(process_batch, batch, i * batch_size, query, window_size, memory_log, pages_per_chunk): i for i, batch in enumerate(batches)}
        
        results = []
        for future in as_completed(future_to_batch):
            batch_index = future_to_batch[future]
            try:
                result = future.result()
                results.append((batch_index, result))
            except Exception as exc:
                print(f'Batch {batch_index} generated an exception: {exc}')
        
        # Sort results by batch_index to ensure order
        results.sort(key=lambda x: x[0])
        combined_summaries = [result for _, result in results]

    return combined_summaries

# ### difference is that we're asking the model to preserve the original language 


coherence_template = """
As a Legal Clerk, your task is to review the provided bullet point summary and reorganize it into a more coherent and well-structured format. Please follow these steps to improve the summary:

1. Carefully review the bullet point summary and identify all the points and key details, paying special attention to names, policy or rule violations, events, actions, disciplinary actions such as suspensions and terminations, dates, locations, case numbers, and legal references.

2. Organize the bullet points in chronological order, ensuring that the sequence of events is accurately represented and that all relevant details are included.

3. Factual Accuracy:
   - DO NOT include any details not explicitly stated in either summary.

4. Ensure that the reorganized bullet points:
   - Present a clear, logical progression of events, with all relevant details included
   - Use concise and unambiguous language
   - Do not introduce any new information or infer details not explicitly stated in the original summary

IMPORTANT
Provide your response in a format similar to the examples below:

**Example**:
Incident Overview:
- Brief description of the incident, including date, location, and involved parties
- Overview of the alleged misconduct and the department's response

Details of Alleged Misconduct:
- How and when the alleged misconduct was discovered
- Details about the evidence that led to the discovery
- Specific policy violation or rule violation

Officer's Statement and Context:
- Officer's admission or denial of the allegations
- Any contextual information provided by the officer to explain their actions

Witness Statements:
- Relevant information provided by witnesses, if applicable
- How witness statements support or contradict the officer's account

Investigation Findings:
- Summary of the investigation's findings
- Specific violations of department policies or regulations
- Disciplinary action

Complaint and Recommended Disciplinary Action:
- Details about the formal complaint filed against the officer
- Recommended disciplinary actions based on the investigation's findings

Case Status:
- Current status of the case and any pending actions
- Brief summary of the key points and conclusion of the report

## Original Bullet Point Summary ##:
{bulletpoint_summary}

Reorganized Bullet Point Summary:
"""

improvement_template = """
As a Legal Clerk, your task is to produce a verified bullet point summary by comparing an updated bullet point summary with the original bullet point summary. The goal is to create a final summary that captures all the essential information from both summaries, ensuring accuracy, coherence, and logical structure. Please follow these steps:

1. Carefully review both summaries and identify all the key points and details, paying special attention to specific names, policy or rule violations, disciplinary actions. events, actions, titles, dates, locations, and case numbers. Update the summary with any key details that are missing.

2. Ensure that the information is organized as bullet points into logical sections, such as those in the example below, with related points grouped under headers and presented in a clear chronological sequence.

3. Factual Accuracy:
   - DO NOT include any details not explicitly stated in either summary.

4. Verify that the final summary:
   - Includes all relevant information from both the updated and original summaries
   - Presents a coherent and logically structured account of the events
   - Uses clear and concise language
   - Does not introduce any new information or infer details not explicitly stated in either summary

IMPORTANT
Provide your response in a format similar to the examples below. Only include headers that are relevant to improving an understanding of the case. 

**Example**:
Incident Overview:
- Brief description of the incident, including date, location, and involved parties
- Overview of the alleged misconduct and the department's response

Details of Alleged Misconduct:
- Details about the specific policy violation or rule violation
- How and when the alleged misconduct was discovered
- Details about the evidence that led to the discovery

Officer's Statement and Context:
- Officer's admission or denial of the allegations
- Any contextual information provided by the officer to explain their actions

Witness Statements:
- Relevant information provided by witnesses, if applicable
- How witness statements support or contradict the officer's account

Investigation Findings:
- Summary of the investigation's findings
- Specific violations of department policies or regulations
- Disciplinary action

Complaint and Recommended Disciplinary Action:
- Details about the formal complaint filed against the officer
- Recommended disciplinary actions based on the investigation's findings

Case Status:
- Current status of the case and any pending actions
- Brief summary of the key points and conclusion of the report

## Updated Bullet Point Summary ##:
{coherent_summary}

## Original Bullet Point Summary ##:
{bulletpoint_summary}

## Return the Updated Bullet Point Summary or the Verified Bullet Point Summary Below ##:
"""

def format_and_improve_summary(bulletpoint_summary, summaries, memory_log):
    
    # Format bulletpoint summary into coherent narrative
    prompt_response = ChatPromptTemplate.from_template(coherence_template)
    response_chain = prompt_response | llm | StrOutputParser()
    coherent_summary = response_chain.invoke({"bulletpoint_summary": bulletpoint_summary})
    coherent_memory_log = response_chain.invoke({"bulletpoint_summary": memory_log})
    
    # Improve coherent summary based on comparison with bulletpoint summary
    prompt_response = ChatPromptTemplate.from_template(improvement_template)
    response_chain = prompt_response | llm | StrOutputParser()
    improved_summary = response_chain.invoke({
        "coherent_summary": coherent_summary,
        "bulletpoint_summary": bulletpoint_summary
    })
    
    improved_memory_log = response_chain.invoke({
        "coherent_summary": coherent_memory_log,
        "bulletpoint_summary": memory_log
    })
    
    return improved_summary, improved_memory_log


final_combine_template = """
As a Legal Clerk, your task is to meticulously combine the provided summaries into a single, comprehensive, and well-organized summary. This summary should include ALL relevant information from both the current combined summary and the new page summary, presented in a detailed, chronological, and coherent manner without any duplication.

## Guidelines ##:

1. Comprehensive Information Integration:
   - Review both summaries thoroughly and include ALL relevant information, no matter how minor it may seem.
   - Ensure inclusion of the following elements (if present in either summary):
     a. All individuals mentioned (names, roles, identifiers)
     b. All events, incidents, or proceedings (with exact dates and locations)
     c. All legal issues, claims, or charges
     d. All policies, laws, or regulations referenced
     e. All actions taken by any party
     f. All evidence mentioned (physical, testimonial, or documentary)
     g. All decisions, rulings, or outcomes
     h. All recommendations or proposed actions
     i. Current status of any ongoing matters
     j. Any contextual or background information

2. Handling Contradictions and Uncertainties:
   - If there are inconsistencies between the summaries, include all versions and clearly note the discrepancy.
   - If information is unclear or seems incomplete, include it as is and note the uncertainty.

3. Factual Accuracy and Completeness:
   - Include ALL details from both summaries, even if they seem redundant or minor.
   - Do not omit any information or make assumptions about its relevance.

4. Formatting for Clarity:
   - Organize information into logical sections (e.g., "Background," "Key Events," "Legal Proceedings," "Evidence," "Outcomes").
   - Use bullet points for easy readability.
   - Present information chronologically within each section where applicable.

5. Preserving Context:
   - Ensure that the relationship between different pieces of information is clear.
   - Maintain any cause-and-effect relationships present in the original summaries.

Current Summary:
{current_summary}

New Summary:
{new_summary}

## Updated Combined Summary: ##
"""

final_verification_template = """
As a Legal Clerk, your task is to meticulously review the updated summary and ensure it captures ALL information and specific details from both the current summary and the new summary. The final summary should be comprehensive, accurate, and well-organized.

Please follow these steps:

1. Comparative Analysis:
   - Carefully compare the updated summary against both the current summary and the new summary.
   - Ensure NO information has been lost in the combination process.

2. Comprehensive Verification:
   Verify that ALL of the following elements from both summaries are present in the updated summary:
   a. All individuals mentioned (names, roles, identifiers)
   b. All events, incidents, or proceedings (with exact dates and locations)
   c. All legal issues, claims, or charges
   d. All policies, laws, or regulations referenced
   e. All actions taken by any party
   f. All evidence mentioned (physical, testimonial, or documentary)
   g. All decisions, rulings, or outcomes
   h. All recommendations or proposed actions
   i. Current status of any ongoing matters
   j. Any contextual or background information

3. Structural Integrity:
   Ensure the summary is formatted clearly with:
   - Logical sections (e.g., "Background," "Key Events," "Legal Proceedings," "Evidence," "Outcomes")
   - Bullet points for easy readability
   - Chronological order within sections where applicable

4. Consistency and Clarity:
   - Check for any missing, inconsistent, or unclear information.
   - Ensure all information is presented in a clear and unambiguous manner.

5. Preservation of Detail:
   - Include ALL details from both summaries, even if they seem redundant or minor.
   - Do not omit any information or make assumptions about its relevance.

6. Handling of Discrepancies:
   - If there are contradictions or inconsistencies, ensure all versions are included with clear notations.

7. Contextual Accuracy:
   - Verify that the relationships between different pieces of information are clear and accurate.
   - Ensure any cause-and-effect relationships from the original summaries are maintained.

Current Summary:
{current_summary}

New Summary:
{new_summary}

Updated Summary:
{updated_summary}

## Return the Verified Summary or Return the Contents of The Updated Summary if No Changes Are Needed. Return this Summary Without Reference To Your Verification Check ##:
"""

aggregation_template_final = """
As a Legal Clerk, your task is to aggregate and synthesize the summaries produced by three different language models. Your goal is to create a comprehensive, accurate, and coherent summary that incorporates all critical information from each model's output. Follow these guidelines:

1. Comprehensive Analysis:
   - Carefully analyze the three summaries for consistency, complementary information, and any discrepancies.
   - Ensure that no critical information is lost in the aggregation process.

2. Information Integration:
   Identify and include ALL of the following elements from each summary (if present):
   a. Type of legal document and its purpose
   b. All individuals mentioned (names, roles, identifiers such as badge numbers)
   c. All events, incidents, or proceedings (with exact dates and locations)
   d. All legal issues, allegations, charges, or rule violations
   e. All policies, laws, regulations, or procedures referenced
   f. All actions taken by any party
   g. All evidence mentioned (physical, testimonial, or documentary)
   h. All investigation steps, findings, and conclusions
   i. All legal proceedings, motions, or resolutions
   j. All decisions, rulings, disciplinary actions, or outcomes
   k. Current status of any ongoing matters
   l. Any pending actions or future proceedings
   m. Any contextual or background information

3. Structural Organization:
   - Combine the information to create a unified, non-redundant summary that presents a clear chronological narrative of the case.
   - Maintain a bullet-point format for clarity and readability.
   - Organize information under relevant headings such as:
     * Document Overview
     * Background Information
     * Key Parties Involved
     * Chronology of Events
     * Allegations or Charges
     * Investigation Process
     * Evidence and Findings
     * Legal Proceedings
     * Outcomes and Decisions
     * Current Status and Next Steps

4. Accuracy and Detail:
   - Ensure that all key details are accurately represented, including full names, dates, locations, and specific legal or procedural information.
   - Include all relevant information, even if it appears in only one of the summaries.

5. Handling Discrepancies:
   - If there are conflicting pieces of information between the summaries, include all versions with a clear note about the discrepancy.
   - If information is unclear or seems incomplete in all summaries, include it as is and note the uncertainty.

6. Relevance and Context:
   - Include all information that contributes to understanding the core aspects of the case.
   - Provide enough context for each point to be understood without referring to the full document.
   - Ensure that the relationships between different pieces of information are clear.

7. Objectivity:
   - Present information in an objective manner, without interpretation or speculation.
   - Use clear, precise, and unambiguous language.

## Model 1 Summary ##
{summary_1}

## Model 2 Summary ##
{summary_2}

## Model 3 Summary ##
{summary_3}

Based on these guidelines, provide the aggregated summary below, ensuring it captures ALL critical information while maintaining a clear, comprehensive, and well-organized narrative:

Aggregated Summary:
"""


condensed_summary_template = """
As a Legal Clerk, your task is to create a concise, high-level summary of the provided document. This condensed summary should be between 1-5 paragraphs in length, focusing on the most essential information while ensuring no critical details are omitted.

Guidelines:

1. Essential Information:
   Identify and include ALL of the following key elements (if present in the document):
   a. Type of legal document and its purpose
   b. Primary parties involved (names and roles)
   c. Key legal issues, claims, or charges
   d. Critical events or incidents (with dates)
   e. Main findings or decisions
   f. Significant evidence or testimonies
   g. Important outcomes or rulings
   h. Current status of the matter
   i. Any pending actions or future proceedings

2. Structure and Flow:
   - Organize the summary in paragraphs, ensuring a logical flow of information.
   - Begin with an introductory sentence stating the type of document and its overall purpose.
   - Present information in a generally chronological order, if applicable to the document type.

3. Comprehensiveness vs. Conciseness:
   - While condensing, ensure that no critical information is omitted.
   - Prioritize information based on its significance to the overall legal matter.
   - Include brief mentions of secondary details if they provide important context.

4. Clarity and Objectivity:
   - Use clear, precise, and unambiguous language.
   - Maintain an objective tone, avoiding interpretation or speculation.
   - If there are significant contradictions or uncertainties in the document, briefly note them.

5. Contextual Relevance:
   - Provide enough context for each point to be understood without referring to the full document.
   - Ensure that the relationships between different pieces of information are clear.

Final Summary:
{final_summary}

## Condensed High-Level Summary: ##
"""

condensed_summary_aggregation_template = """
As a Legal Clerk, your task is to aggregate and synthesize the condensed summaries produced by three different language models into a final, comprehensive yet concise high-level summary. This final condensed summary should be between 1-5 paragraphs in length and capture the essence of the legal document.

Guidelines:

1. Comparative Analysis:
   - Analyze the three condensed summaries for consistency, complementary information, and any discrepancies.

2. Comprehensive Integration:
   Ensure the final summary includes ALL of the following elements (if present in any of the summaries):
   a. Type of legal document and its purpose
   b. Primary parties involved (names and roles)
   c. Key legal issues, claims, or charges
   d. Critical events or incidents (with dates)
   e. Main findings or decisions
   f. Significant evidence or testimonies
   g. Important outcomes or rulings
   h. Current status of the matter
   i. Any pending actions or future proceedings

3. Structural Integrity:
   - Begin with an introductory sentence stating the type of document and its overall purpose.
   - Organize the summary in paragraphs, ensuring a logical and chronological (if applicable) flow of information.

4. Information Synthesis:
   - Combine information to create a unified, non-redundant summary that provides a clear overview of the document.
   - Ensure all critical details are accurately represented, without omitting any significant information present in any of the three summaries.

5. Clarity and Objectivity:
   - Use clear, precise, and unambiguous language.
   - Maintain an objective tone, avoiding interpretation or speculation.

6. Handling Discrepancies:
   - If there are conflicting pieces of information, include all versions with a brief note about the discrepancy.
   - If information is unclear or seems incomplete in all summaries, note this uncertainty in the final summary.

7. Contextual Relevance:
   - Provide enough context for each point to be understood without referring to the full document.
   - Ensure that the relationships between different pieces of information are clear.

## Model 1 Condensed Summary ##
{summary_1}

## Model 2 Condensed Summary ##
{summary_2}

## Model 3 Condensed Summary ##
{summary_3}

Based on these guidelines, provide the final aggregated condensed summary below:

Final Condensed Summary:
"""

# New template for improving the condensed summary
improve_condensed_summary_template = """
As a Legal Clerk, your task is to review and potentially improve the final condensed summary of a legal document. You will be provided with the current condensed summary and a memory log containing additional information from the document processing. Your goal is to enhance the condensed summary by incorporating any relevant missing information from the memory log.

Guidelines:

1. Review the current condensed summary and the memory log carefully.
2. Identify any significant information in the memory log that is not present in the condensed summary.
3. If you find relevant missing information, integrate it into the condensed summary while maintaining its concise nature (1-5 paragraphs).
4. Ensure that the additional information genuinely enhances the summary's comprehensiveness and relevance.
5. Maintain the original structure and flow of the condensed summary as much as possible.
6. If no significant improvements are needed, return the original condensed summary unchanged.

Current Condensed Summary:
{condensed_summary}

Memory Log:
{memory_log}

Please provide the improved condensed summary below. If no improvements are needed, simply reproduce the original summary:

Improved Condensed Summary:
"""

improved_summary_integration_prompt = """
# Improved Summary Integration Prompt

As a Legal Clerk, your task is to review, integrate, and potentially improve the final condensed summary of a legal document. You will be provided with the current final condensed summary and all individual summaries from the document processing. Your goal is to enhance the condensed summary by incorporating any relevant missing information from the individual summaries, ensuring a comprehensive yet concise overview of the legal document.

## Guidelines:

1. Review the current final condensed summary and all individual summaries carefully.
2. Identify any significant information in the individual summaries that is not present in the final condensed summary.
3. If you find relevant missing information, integrate it into the condensed summary while maintaining its concise nature (1-5 paragraphs).
4. Ensure that the additional information genuinely enhances the summary's comprehensiveness and relevance.
5. Maintain the original structure and flow of the condensed summary as much as possible.
6. If no significant improvements are needed, return the original condensed summary unchanged.

## Key Elements to Include (if present in any of the summaries):

a. Type of legal document and its purpose
b. Primary parties involved (names and roles)
c. Key legal issues, claims, or charges
d. Critical events or incidents (with dates)
e. Main findings or decisions
f. Significant evidence or testimonies
g. Important outcomes or rulings
h. Current status of the matter
i. Any pending actions or future proceedings

## Structural Integrity:

- Begin with an introductory sentence stating the type of document and its overall purpose.
- Organize the summary in paragraphs, ensuring a logical and chronological (if applicable) flow of information.

## Information Synthesis:

- Combine information to create a unified, non-redundant summary that provides a clear overview of the document.
- Ensure all critical details are accurately represented, without omitting any significant information present in any of the summaries.

## Clarity and Objectivity:

- Use clear, precise, and unambiguous language.
- Maintain an objective tone, avoiding interpretation or speculation.

## Handling Discrepancies:

- If there are conflicting pieces of information, include all versions with a brief note about the discrepancy.
- If information is unclear or seems incomplete in all summaries, note this uncertainty in the final summary.

## Contextual Relevance:

- Provide enough context for each point to be understood without referring to the full document.
- Ensure that the relationships between different pieces of information are clear.

Current Final Condensed Summary:
{final_condensed_summary}

All Individual Summaries:
{all_summaries}

Please provide the improved final condensed summary below. If no improvements are needed, simply reproduce the original summary:

Summary:
"""

def combine_final_summaries(summaries, memory_log):
    combiner_llm_1 = llm_1
    combiner_llm_2 = llm_2
    combiner_llm_3 = llm_3
    aggregator_llm = llm_4
    verification_llm = llm_3
    condensed_summary_llm_1 = llm_3
    condensed_summary_llm_2 = llm_3
    condensed_summary_llm_3 = llm_3
    condensed_summary_aggregator_llm = llm_4
    improved_summary_llm = llm_4

    combine_prompt_template = ChatPromptTemplate.from_template(final_combine_template)
    aggregation_prompt_template = ChatPromptTemplate.from_template(aggregation_template_final)
    verification_prompt_template = ChatPromptTemplate.from_template(final_verification_template)
    condensed_summary_prompt_template = ChatPromptTemplate.from_template(condensed_summary_template)
    condensed_summary_aggregation_prompt_template = ChatPromptTemplate.from_template(condensed_summary_aggregation_template)
    improve_condensed_summary_prompt_template = ChatPromptTemplate.from_template(improve_condensed_summary_template)
    improved_summary_integration_prompt_template = ChatPromptTemplate.from_template(improved_summary_integration_prompt)

    combine_chain_1 = combine_prompt_template | combiner_llm_1 | StrOutputParser()
    combine_chain_2 = combine_prompt_template | combiner_llm_2 | StrOutputParser()
    combine_chain_3 = combine_prompt_template | combiner_llm_3 | StrOutputParser()
    aggregation_chain = aggregation_prompt_template | aggregator_llm | StrOutputParser()
    verification_chain = verification_prompt_template | verification_llm | StrOutputParser()
    condensed_summary_chain_1 = condensed_summary_prompt_template | condensed_summary_llm_1 | StrOutputParser()
    condensed_summary_chain_2 = condensed_summary_prompt_template | condensed_summary_llm_2 | StrOutputParser()
    condensed_summary_chain_3 = condensed_summary_prompt_template | condensed_summary_llm_3 | StrOutputParser()
    condensed_summary_aggregation_chain = condensed_summary_aggregation_prompt_template | condensed_summary_aggregator_llm | StrOutputParser()
    improve_condensed_summary_chain = improve_condensed_summary_prompt_template | improved_summary_llm | StrOutputParser()
    improved_summary_integration_chain = improved_summary_integration_prompt_template | improved_summary_llm | StrOutputParser()

    current_summary = summaries[0][0]["page_content"]

    for i in range(1, len(summaries)):
        new_summary = summaries[i][0]["page_content"]
        
        # Generate summaries using three different models
        summary_1 = combine_chain_1.invoke({
            "current_summary": current_summary,
            "new_summary": new_summary
        })
        summary_2 = combine_chain_2.invoke({
            "current_summary": current_summary,
            "new_summary": new_summary
        })
        summary_3 = combine_chain_3.invoke({
            "current_summary": current_summary,
            "new_summary": new_summary
        })

        # Aggregate the summaries
        aggregated_summary = aggregation_chain.invoke({
            "summary_1": summary_1,
            "summary_2": summary_2,
            "summary_3": summary_3
        })

        # Verify the aggregated summary
        final_updated_summary = verification_chain.invoke({
            "current_summary": current_summary,
            "new_summary": new_summary,
            "updated_summary": aggregated_summary
        })
        
        current_summary = final_updated_summary

    final_summary = current_summary

    # Generate condensed summaries using three different models
    condensed_summary_1 = condensed_summary_chain_1.invoke({
        "final_summary": final_summary
    })
    condensed_summary_2 = condensed_summary_chain_2.invoke({
        "final_summary": final_summary
    })
    condensed_summary_3 = condensed_summary_chain_3.invoke({
        "final_summary": final_summary
    })

    # Aggregate the condensed summaries
    final_condensed_summary = condensed_summary_aggregation_chain.invoke({
        "summary_1": condensed_summary_1,
        "summary_2": condensed_summary_2,
        "summary_3": condensed_summary_3
    })

    # Improve the final condensed summary using the memory log
    improved_condensed_summary = improve_condensed_summary_chain.invoke({
        "condensed_summary": final_condensed_summary,
        "memory_log": memory_log
    })

    # Create a new improved summary using all individual summaries
    all_summaries = "\n\n".join([summary[0]["page_content"] for summary in summaries])
    improved_final_summary = improved_summary_integration_chain.invoke({
        "final_condensed_summary": final_condensed_summary,
        "all_summaries": all_summaries
    })

    return {
        "page_content": final_summary,
        "final_condensed_summary": final_condensed_summary,
        "improved_condensed_summary": improved_condensed_summary,
        "improved_final_summary": improved_final_summary
    }, memory_log


def save_summaries_to_json(summary, output_file, start_page, end_page):
    output_data = [
        {
            "sentence": summary["improved_final_summary"],
            "filename": os.path.basename(output_file),
            "start_page": start_page,
            "end_page": end_page,
        }
    ]
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
                memory_log = create_memory_log(docs)
                query = "Generate a timeline of events based on the police report."
                combined_summaries = generate_summaries(docs, query, memory_log, custom_template)
                final_summary, memory_log = combine_final_summaries(
                    combined_summaries, memory_log
                )
                start_page = docs[0].metadata["seq_num"]
                end_page = docs[-1].metadata["seq_num"]

                output_data.append(
                    save_summaries_to_json(final_summary, entry, start_page, end_page)
                )

            elif os.path.isdir(entry_path):
                # Process directory containing JSON files
                for filename in os.listdir(entry_path):
                    if filename.endswith(".json"):
                        input_file_path = os.path.join(entry_path, filename)

                        docs = load_and_split(
                            input_file_path
                        )  # Changed from entry_path to input_file_path
                        memory_log = create_memory_log(docs)
                        query = (
                            "Generate a timeline of events based on the police report."
                        )
                        combined_summaries = generate_summaries(docs, query, memory_log, custom_template)
                        final_summary, memory_log = combine_final_summaries(
                            combined_summaries, memory_log
                        )
                        start_page = docs[0].metadata["seq_num"]
                        end_page = docs[-1].metadata["seq_num"]
                        output_data.append(
                            save_summaries_to_json(
                                final_summary, entry, start_page, end_page
                            )
                        )

        # Convert the output data to JSON string
        with open(output_path, "w") as output_file:
            json.dump(output_data, output_file, indent=4)

    except Exception as e:
        logger.error(f"Error processing JSON: {str(e)}")
        print(json.dumps({"success": False, "message": "Failed to process JSON"}))
        sys.exit(1)

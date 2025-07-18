import os
import requests
from bs4 import BeautifulSoup
from services.agent.grounding.analyse_material.analyse_material_service import extract_web_content
from services.agent.grounding.vector_search_retrieval.vector_search_service import query_OERs, query_documents_with_filter
from services.agent.grounding.vector_search_retrieval.vector_search_utils import VectorSearchResults

from .agent_utils import GroundingSteps, OERs_grounding_prompt, OERsGroundingResponse, UserGroundingRequest, UserGroundingResponse, WebGroundingResponse, WebSearchResults, user_resources_grounding_prompt, web_grounding_prompt, websites_selection_prompt
from ..chat.chat_utils import Message, ResourceDocumentSimplified
from typing import List, Tuple
from motor.motor_asyncio import AsyncIOMotorCollection

from services.llm_integration.gemini import GeminiLLM

GOOGLE_SEARCH_API_KEY = os.getenv("GOOGLE_SEARCH_API_KEY", "YOUR_GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID", "YOUR_CUSTOM_SEARCH_ENGINE_ID")

def fetch_page_summary(url: str) -> str:
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}  # pretend to be a browser
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Try to get <meta name="description">
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content'].strip()

        # Fallback: get first <p> tag content
        first_p = soup.find('p')
        if first_p:
            return first_p.get_text(strip=True)

        # If all fails
        print("No description or paragraph found.")
        return ""

    except Exception as e:
        return f"Error fetching {url}: {e}"

def google_cse_search(query, api_key, cse_id, num=5) -> Tuple[str, List[WebGroundingResponse]]:
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "q": query,
        "key": api_key,
        "cx": cse_id,
        "num": num
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    
    results: List[WebGroundingResponse] = []
    for item in data.get("items", []):
        title = item.get("title")
        link = item.get("link")
        summary = fetch_page_summary(link)
        print(f"Title: {title}, Link: {link}, Summary: {summary}")
        web_result = WebGroundingResponse(title=title, url=link, summary=summary)
        results.append(web_result)
    final_results: Tuple[str, List[WebGroundingResponse]] = (query, results)
    return final_results

async def ground_response(user_collection: AsyncIOMotorCollection, chat_id, source: GroundingSteps, resources: List[str], queries: str, language: str, intent: str, reasoning: str, model: str = "GEMINI") -> str:
    """
    Grounds the query using the provided resources.
    """
    # Define the LLM object
    if model is None:
        model = "GEMINI"
    if model.upper() == "GEMINI":
        llm = GeminiLLM()
    else:
        llm = GeminiLLM()
    queries = queries.split('\n')
    grounded_material = ""

    if source == GroundingSteps.USER_RESOURCES:
        print("Grounding using user resources...")
        # Get user resources for this chat
        from services.agent.orchestrator.chat.chat_service import get_chat_resources
        chat_resources: List[ResourceDocumentSimplified] = await get_chat_resources(user_collection, chat_id)
        # Get the name of the user collection
        collection_name = user_collection.name
        # order resources by updated_at (most recent first)
        chat_resources.sort(key=lambda x: x.uploaded_at, reverse=True)
        
        # Convert to string for the LLM to read
        resources_string = "Available User Resources:\n".join([resource.to_str() for resource in chat_resources])
        # Generate a prompt for the LLM
        grounding_request = UserGroundingRequest(
                                language=language,
                                user_intent=intent,
                                queries=queries,
                                resources_string=resources_string
                            )
        prompt = user_resources_grounding_prompt(grounding_request)
        if resources is not None:
            prompt += f"\nConsider that the user just uploaded the resources with IDs: {resources}"
        try:
            response: UserGroundingResponse = llm.generate_text(prompt=prompt, response_model=UserGroundingResponse)
            print(f"User Docs Query Grounding response: {response.grounding}")
        except Exception as e:
            print(f"Error during grounding llm call on user resources: {e}")
            raise

        # Perform vector serach on those resources
        results: List[VectorSearchResults] = await query_documents_with_filter(response.grounding, collection_name)
        grounded_material: str = "\n".join([result.to_str() for result in results])

    
    elif source == GroundingSteps.OERS:
        print("Grounding using OERs...")
        grounding_request = UserGroundingRequest(
                                language=language,
                                user_intent=intent,
                                queries=queries,
                                resources_string=""
                            )
        # Generate rich queries
        prompt = OERs_grounding_prompt(grounding_request)
        try:
            OERresponse: OERsGroundingResponse = llm.generate_text(prompt=prompt, response_model=OERsGroundingResponse)
            print(f"OERs Query Grounding response: {OERresponse.queries}")
        except Exception as e:
            print(f"Error during grounding llm call on user resources: {e}")
            raise
        # Query the OERs database
        results: List[VectorSearchResults] = await query_OERs(OERresponse.queries)
        grounded_material: str = "\n".join([result.to_str() for result in results])

    else: # web_search
        # Perform a web search using Google Custom Search API
        print("Grounding using web search...")
        api_key = GOOGLE_SEARCH_API_KEY
        cse_id = GOOGLE_CSE_ID
        web_search_results: List[Tuple[str, List[WebGroundingResponse]]] = []
        web_grounding_request = UserGroundingRequest(
                                language=language,
                                user_intent=intent,
                                queries=queries,
                                resources_string=""
                            )
        # Generate rich queries
        prompt = web_grounding_prompt(web_grounding_request)
        try:
            web_queries: OERsGroundingResponse = llm.generate_text(prompt=prompt, response_model=OERsGroundingResponse)
            print(f"\nWeb Query Grounding response: {web_queries.queries}\n")
        except Exception as e:
            print(f"Error during grounding llm call on user resources: {e}")
            raise
        
        queries = web_queries.queries
        for query in queries:
            try:
                results: Tuple[str, List[WebGroundingResponse]] = google_cse_search(query, api_key, cse_id)
                web_search_results.append(results)
                
            except Exception as e:
                print(f"Error during web search: {e}")
                raise
        
        # LLM call to choose best websites
        output = []
        for query, responses in web_search_results:
            output.append(f"Query: {query}")
            for idx, res in enumerate(responses, 1):
                output.append(
                    f"  Result {idx}:\n"
                    f"    Title: {res.title}\n"
                    f"    URL: {res.url}\n"
                    f"    Summary: {res.summary}\n"
                )
        web_search_results_string = f"\nReasoning: {web_queries.reasoning}\n".join(output) 
        prompt = websites_selection_prompt(
            websites=web_search_results_string,
            intent=intent,
            reasoning=reasoning,
            language=language
        )
        try:
            web_response: WebSearchResults = llm.generate_text(prompt=prompt, response_model=WebSearchResults)
            print(f"Selected websites {web_response}")
        except Exception as e:
            print(f"Error during grounding llm call on web search: {e}")
            raise

        # For each result, get the complete website text
        grounded_material: str = web_response.reasoning
        for website in web_response.selected_websites:
            # Add summary, title, and url
            grounded_material += f"\n\nQuery: {website.summary}\nTitle: {website.title}\nURL: {website.url}"
            # Add website text
            website_text = extract_web_content(website.url)
            grounded_material += f"\nWebsite Text:\n{website_text}\n\n"
            
    print(f"Grounded material: {grounded_material[:100]}")

    return grounded_material





def grounding_to_string(grounding: List[str]) -> str:
    """
    Converts the grounded material to a string format.
    """
    # Placeholder for the actual implementation
    return "Grounded material string"

def tool_call(tool_name: str, tool_parameters: dict) -> str:
    """
    Calls a tool and returns the response.
    """
    # Placeholder for the actual implementation
    return "Tool response"

def map_response_to_message(response: str) -> Message:
    """
    Maps the response from the LLM to a Message object.
    """
    # Placeholder for the actual implementation
    return Message(
        role="assistant",
        content=response,
        timestamp=None,
        in_memory=False,
        resources=[]
    )

def plan_next_message(action: str) -> Message:
    """
    Plans the next message based on the action.
    """
    # Placeholder for the actual implementation
    return Message(
        role="assistant",
        content="Next message content",
        timestamp=None,
        in_memory=False,
        resources=[]
    )


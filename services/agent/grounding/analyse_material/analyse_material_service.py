from PIL.Image import Image
from google import genai
from dotenv import load_dotenv
from .analyse_material_utils import AnalyseMaterialRequest, AnalyseMaterialResponse, Analysis, analyse_material_prompt, analyse_image_prompt, Topic
from ....llm_integration.gemini import GeminiLLM
import os
from typing import List
from urllib.parse import urlparse, urlunparse, parse_qs
import re
from langchain_core.documents import Document

# File Handling Libraries
from pathlib import Path
import pdfplumber
# from docx import Document as DocxDocument
from pptx import Presentation

# OCR Libraries
import pytesseract
from pdf2image import convert_from_path

# Web Scraping Libraries
import requests
from bs4 import BeautifulSoup
import yt_dlp

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY", "")

client = genai.Client(api_key=API_KEY)

# --- Helper Functions ---
def is_url(text: str) -> bool:
    """Check if the text is a valid URL."""
    try:
        result = urlparse(text)
        return all([result.scheme, result.netloc])
    except:
        return False

def is_youtube_url(url: str) -> bool:
    """Check if the URL is a YouTube video link."""
    try:
        parsed = urlparse(url)
        if parsed.netloc in ["www.youtube.com", "youtube.com", "youtu.be"]:
            return True
        return False
    except:
        return False

def clean_youtube_url(url: str) -> str:
    """
    Cleans a YouTube URL by removing all optional parameters except the video ID.
    """
    try:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)

        # Extract the video ID (v parameter)
        video_id = query_params.get('v', [None])[0]

        if video_id:
            # Reconstruct the URL with only the video ID
            clean_query = f"v={video_id}"
            clean_url = urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, '', clean_query, ''))
            return clean_url
        else:
            return url  # Return original URL if video ID is not found
    except Exception:
        return url  # Return original URL in case of parsing errors

def get_youtube_captions(url: str, preferred_lang: str = "en") -> str:
    """
    Download captions from a YouTube video using yt-dlp.
    Returns the captions as plain text.
    """
    # Clean the URL
    cleaned_url = clean_youtube_url(url)

    ydl_opts = {
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitlesformat': 'vtt',
        'subtitleslangs': [preferred_lang],
        'outtmpl': '%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(cleaned_url, download=False)
        subs = info.get('subtitles') or info.get('automatic_captions')
        if not subs or preferred_lang not in subs:
            raise ValueError("No captions found for this video.")
        # Download the subtitle file
        ydl.download([cleaned_url])
        # Find the downloaded .vtt file
        video_id = info['id']
        vtt_file = f"{video_id}.{preferred_lang}.vtt"
        if not os.path.exists(vtt_file):
            vtt_file = f"{video_id}.{preferred_lang}.auto.vtt"
        if not os.path.exists(vtt_file):
            raise ValueError("Subtitle file not found after download.")
        # Read and clean the VTT file
        with open(vtt_file, 'r', encoding='utf-8') as f:
            vtt_text = f.read()
        # Remove VTT formatting
        text = re.sub(r"(\d{2}:\d{2}:\d{2}\.\d{3} --> .*)", "", vtt_text)
        text = re.sub(r"WEBVTT.*", "", vtt_text)
        text = re.sub(r"\n+", "\n", text)
        text = text.strip()
        # Optionally, delete the file after reading
        os.remove(vtt_file)
        return text
    
def clean_web_text(text: str) -> str:
    """
    Clean extracted web text by removing common noise patterns.
    This is a basic implementation - can be enhanced based on specific needs.
    """
    # Remove excessive whitespace and newlines
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r' +', ' ', text)

    # Remove common navigation/footer patterns
    patterns_to_remove = [
        r'Cookie Policy.*?$',
        r'Privacy Policy.*?$',
        r'Terms of Service.*?$',
        r'Subscribe to.*?newsletter.*?$',
        r'Follow us on.*?$',
        r'Copyright.*?$',
        r'All rights reserved.*?$',
        r'Share this.*?$',
        r'Print this.*?$',
        r'Email this.*?$',
        r'Tweet.*?$',
        r'Facebook.*?$',
        r'LinkedIn.*?$',
        r'Instagram.*?$',
        r'YouTube.*?$',
        r'Advertisement.*?$',
        r'Sponsored.*?$',
        r'Related Articles.*?$',
        r'You may also like.*?$',
        r'More from.*?$',
        r'Categories:.*?$',
        r'Tags:.*?$',
        r'Filed under:.*?$',
        r'Jump to navigation.*?$',
        r'Skip to.*?$',
        r'Menu.*?$',
        r'Search.*?$',
        r'Login.*?$',
        r'Register.*?$',
        r'Sign up.*?$',
        r'Contact us.*?$',
        r'About us.*?$',
        r'Help.*?$',
        r'FAQ.*?$',
    ]

    for pattern in patterns_to_remove:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)

    # Remove lines that are likely navigation or metadata (very short lines with common words)
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        # Skip very short lines that contain common navigation words
        if len(line) < 10 and any(word in line.lower() for word in ['home', 'about', 'contact', 'menu', 'search', 'login', 'register']):
            continue
        # Skip lines that are mostly punctuation or numbers
        if len(line) > 0 and len(re.sub(r'[^\w\s]', '', line)) / len(line) < 0.5:
            continue
        cleaned_lines.append(line)

    text = '\n'.join(cleaned_lines)

    # Final cleanup
    text = text.strip()
    return text

def extract_web_content(url: str) -> str:
    """Extract text content from a web page."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
            script.decompose()

        # Try to find main content areas first
        main_content = None
        for selector in ['main', 'article', '.content', '#content', '.post', '.entry']:
            main_content = soup.select_one(selector)
            if main_content:
                break

        if main_content:
            text = main_content.get_text()
        else:
            text = soup.get_text()

        # Clean the extracted text
        text = clean_web_text(text)

        return text

    except Exception as e:
        raise ValueError(f"Failed to extract content from URL: {str(e)}")

def read_text_file(file_path: str) -> str:
    """Reads content from a plain text file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def ocr_pdf_page(page_image) -> str:
    """Extract text from a PDF page image using OCR."""
    try:
        text = pytesseract.image_to_string(page_image, lang='eng')
        return text
    except Exception as e:
        #print(f"OCR failed for page: {str(e)}")
        return ""

def read_pdf_file(file_path: str) -> List[Document]:
    """
    Reads content from a PDF file using pdfplumber.
    Uses OCR for pages with less than 10 characters of selectable text.
    Returns a list of Documents, one per page.
    """
    documents = []
    pages_needing_ocr = []

    try:
        with pdfplumber.open(file_path) as pdf:
            #print(f"PDF has {len(pdf.pages)} pages")  # Debug

            for page_num, page in enumerate(pdf.pages):
                page_text = page.extract_text()

                if page_text is None:
                    page_text = ""

                # If page has less than 10 characters, mark for OCR
                if len(page_text.strip()) < 10:
                    pages_needing_ocr.append(page_num)
                    documents.append(Document(page_content=f"[Page {page_num + 1} - OCR processing needed]", metadata={"page": page_num + 1}))  # Placeholder
                else:
                    documents.append(Document(page_content=page_text, metadata={"page": page_num + 1}))

            #print(f"Pages needing OCR: {pages_needing_ocr}")  # Debug

            # Process pages that need OCR
            if pages_needing_ocr:
                #print(f"Converting {len(pages_needing_ocr)} pages to images for OCR...")
                images = convert_from_path(file_path)

                for page_num in pages_needing_ocr:
                    if page_num < len(images):
                        #print(f"Running OCR on page {page_num + 1}...")  # Debug
                        ocr_text = ocr_pdf_page(images[page_num])

                        # Replace the placeholder with actual OCR text
                        for i, doc in enumerate(documents):
                            if doc.metadata.get("page") == page_num + 1 and "[Page" in doc.page_content:
                                documents[i] = Document(page_content=f"[Page {page_num + 1} - OCR]\n{ocr_text}", metadata={"page": page_num + 1})
                                break

            # Debug: Print final extracted text
            #print(f"Final extracted text (first 500 chars): {documents[0].page_content[:100] if documents else 'No Documents'}")

    except Exception as e:
        raise ValueError(f"Failed to read PDF file: {str(e)}")

    return documents

def read_docx_file(file_path: str) -> List[Document]:
    """Reads content from a DOCX file."""
    doc = Document(file_path)
    documents = [Document(page_content=paragraph.text, metadata={"page": i + 1}) for i, paragraph in enumerate(doc.paragraphs)]
    return documents

def read_pptx_file(file_path: str) -> List[Document]:
    """Reads content from a PPTX file."""
    prs = Presentation(file_path)
    documents = []
    slide_num = 1
    for slide in prs.slides:
        slide_text = ""
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                slide_text += shape.text + "\n"
        documents.append(Document(page_content=slide_text, metadata={"page": slide_num}))
        slide_num += 1
    return documents

def analyse_image_with_llm(image: Image) -> str:
    """
    Uses an LLM to analyze the image and extract text.
    This is a placeholder function; actual implementation may vary.
    """
    # Call the LLM with a prompt to analyze the image
    llm = GeminiLLM()
    prompt = analyse_image_prompt()
    response = llm.generate_text(prompt=prompt, image=image)
    return response

def get_text_from_source(text: str) -> List[Document]:
    """
    Determines if the input 'text' is a file path, URL, YouTube URL, or direct text content.
    Extracts and returns the appropriate text content as a list of Document objects.
    """
    # Check if it's a YouTube URL
    if is_youtube_url(text):
        #print(f"Detected YouTube URL: {text}")
        captions = get_youtube_captions(text)
        #print(captions[:500])
        return [Document(page_content=captions, metadata={"source": "youtube"})]

    # Check if it's a regular URL
    if is_url(text):
        #print(f"Detected URL: {text}")
        content = extract_web_content(text)
        return [Document(page_content=content, metadata={"source": "webpage"})]

    # Check if it's a file path
    if len(text) < 4000: 
        file_path = Path(text)
        if file_path.exists():
            file_extension = file_path.suffix.lower()
            if file_extension == ".txt":
                #print(f"Detected text file: {text}")
                content = read_text_file(text)
                return [Document(page_content=content, metadata={"source": "text_file"})]
            elif file_extension == ".pdf":
                #print(f"Detected PDF file: {text}")
                return read_pdf_file(text)
            elif file_extension == ".docx":
                #print(f"Detected DOCX file: {text}")
                return read_docx_file(text)
            elif file_extension == ".pptx":
                #print(f"Detected PPTX file: {text}")
                return read_pptx_file(text)
            elif file_extension in [".jpg", ".jpeg", ".png"]:
                #print(f"Detected image file: {text}")
                # Perform OCR on the image file
                try:
                    image = Image.open(text)
                    ocr_text = pytesseract.image_to_string(image)
                    if ocr_text.len(ocr_text.strip()) < 40:
                        image_text = analyse_image_with_llm(image)
                        if image_text:
                            ocr_text = image_text
                        else:
                            raise ValueError("Image cannot be read.")
                    return [Document(page_content=ocr_text, metadata={"source": "image_file"})]
                except Exception as e:
                    raise ValueError(f"Failed to perform OCR on image file: {str(e)}")
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")
    
    # It's direct text content
    #print("Detected direct text content.")
    return [Document(page_content=text, metadata={"source": "direct_text"})]

def extract_plain_text_from_documents(documents: List[Document]) -> str:
    """
    Extracts the plain text content from a list of Document objects and concatenates it into a single string.
    """
    plain_text = ""
    for doc in documents:
        plain_text += doc.page_content + "\n"  # Add a newline between documents
    return plain_text.strip()  # Remove any trailing whitespace

def chunk_text(text: str, chunk_size: int = 400000) -> List[str]:
    """
    Splits text into chunks of approximately 'chunk_size' characters (≈100k tokens).
    Uses 400k characters as approximation for 100k tokens (1 token ≈ 4 characters).
    """
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

def merge_analysis_responses(responses: List[AnalyseMaterialResponse]) -> AnalyseMaterialResponse:
    """Merges a list of AnalyseMaterialResponse objects into a single object."""
    if not responses:
        raise ValueError("No responses to merge.")

    # Start with the first response
    merged_response = responses[0]

    # Collect topics and keywords from all responses
    all_topics: List[Topic] = []
    all_keywords: List[str] = []

    for response in responses:
        all_topics.extend(response.topics)
        all_keywords.extend(response.keywords)

    # Deduplicate topics and keywords
    unique_topics = []
    seen_topic_names = set()
    for topic in all_topics:
        if topic.topic not in seen_topic_names:  # Changed topic.name to topic.topic
            unique_topics.append(topic)
            seen_topic_names.add(topic.topic)  # Changed topic.name to topic.topic

    unique_keywords = list(set(all_keywords))

    # Update the merged response
    merged_response.topics = unique_topics
    merged_response.keywords = unique_keywords
    # Sum the estimated duration
    merged_response.estimated_duration = sum(response.estimated_duration for response in responses)

    return merged_response

# --- Main Function ---
def analysis(request: AnalyseMaterialRequest) -> Analysis:
    model = request.model
    if model is None:
        model = "GEMINI"
    if model.capitalize() == "GEMINI":
        llm = GeminiLLM()
    else:
        llm = GeminiLLM()

    try:
        # 1. Get text content from source (file, URL, or direct text)
        documents = get_text_from_source(request.text)
        text = extract_plain_text_from_documents(documents)

        # 2. Chunk the text
        chunks = chunk_text(text)

        # 3. Process each chunk with the LLM
        responses: List[AnalyseMaterialResponse] = []
        for i, chunk in enumerate(chunks):
            #print(f"Processing chunk {i + 1}/{len(chunks)}...")
            prompt = analyse_material_prompt(AnalyseMaterialRequest(text=chunk, model=request.model))
            response: AnalyseMaterialResponse = llm.generate_text(prompt=prompt, response_model=AnalyseMaterialResponse)
            #print(f"Chunk {i + 1} response: {response}")
            responses.append(response)

        # 4. Merge the responses
        final_response = merge_analysis_responses(responses)

        # 5. Create the final Analysis object
        final = Analysis(
            language=final_response.language,
            macro_subject=final_response.macro_subject,
            title=final_response.title,
            education_level=final_response.education_level,
            learning_outcome=final_response.learning_outcome,
            topics=final_response.topics,
            keywords=final_response.keywords,
            prerequisites=final_response.prerequisites,
            estimated_duration=final_response.estimated_duration,
        )

    except Exception as e:
        raise ValueError(f"Error during analysis: {str(e)}")

    return final


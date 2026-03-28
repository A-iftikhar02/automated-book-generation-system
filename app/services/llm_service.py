from google import genai
from ..config import settings
import logging

# Set up logging for LLM calls
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the new Gemini Client (google-genai SDK)
client = None
if settings.GEMINI_API_KEY:
    try:
        # Initializing the modern genai Client
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
    except Exception as e:
        logger.error(f"Failed to initialize Gemini Client: {e}")
else:
    logger.warning("GEMINI_API_KEY not found in settings. Gemini services will fail.")

# Model selection - Based on USER instruction & successful test run
MODEL_NAME = "gemini-2.5-flash" 

def generate_outline(title: str, notes: str) -> str:
    """Generates a structured book outline using the modern google-genai SDK."""
    if not client:
        raise ValueError("Gemini Client not initialized. Check API key.")
        
    prompt = f"""
    You are a professional book editor. Create a clean, beginner-friendly book outline based on the following:
    
    Book Title: {title}
    Editor Notes: {notes}
    
    Format the output as a Markdown list of chapters. Each chapter should have a title and a 1-2 sentence description of its purpose.
    Return only the outline text.
    """
    
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )
        if not response or not hasattr(response, 'text'):
            raise ValueError("No response text from Gemini.")
            
        return response.text.strip()
    except Exception as e:
        logger.error(f"Error generating outline with {MODEL_NAME}: {e}")
        # Re-raising for the API to catch and return 502
        raise ValueError(f"Gemini Outline Generation Error ({MODEL_NAME}): {str(e)}")

def generate_chapter(title: str, outline_text: str, chapter_number: int, previous_summaries: str) -> tuple[str, str]:
    """Generates full chapter content and title using the modern google-genai SDK."""
    if not client:
        raise ValueError("Gemini Client not initialized.")
        
    prompt = f"""
    You are an expert novelist writing a book titled '{title}'. 
    
    The overall outline is:
    {outline_text}
    
    You are currently writing Chapter {chapter_number}.
    
    Context from previous chapters:
    {previous_summaries}
    
    Instructions:
    - Maintain consistent narrative style.
    - Avoid repetition of plot points from earlier summaries.
    - Split the response into a Chapter Title and the full Content, separated by '---CONTENT_START---'.
    
    Example response structure:
    The Hidden Valley
    ---CONTENT_START---
    The sun began to set...
    """
    
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )
        if not response or not hasattr(response, 'text'):
            raise ValueError("No response text from Gemini.")
            
        raw_text = response.text.strip()
        
        if "---CONTENT_START---" in raw_text:
            parts = raw_text.split("---CONTENT_START---")
            chapter_title = parts[0].strip()
            chapter_content = parts[1].strip()
        else:
            chapter_title = f"Chapter {chapter_number}"
            chapter_content = raw_text
            
        return chapter_title, chapter_content
    except Exception as e:
        logger.error(f"Error generating chapter {chapter_number} with {MODEL_NAME}: {e}")
        raise ValueError(f"Gemini Chapter Generation Error ({MODEL_NAME}): {str(e)}")

def generate_summary(chapter_content: str) -> str:
    """Creates a concise summary using the modern google-genai SDK."""
    if not client:
        raise ValueError("Gemini Client not initialized.")
        
    prompt = f"""
    Condense the following chapter content into a single, informative summary paragraph (2-3 sentences max).
    Focus on key plot developments.
    
    {chapter_content}
    """
    
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )
        if not response or not hasattr(response, 'text'):
            raise ValueError("No response text from Gemini.")
            
        return response.text.strip()
    except Exception as e:
        logger.error(f"Error generating summary with {MODEL_NAME}: {e}")
        raise ValueError(f"Gemini Summary Generation Error ({MODEL_NAME}): {str(e)}")

def regenerate_outline(title: str, notes_before: str, notes_after: str, previous_outline: str) -> str:
    """Regenerates a book outline based on previous draft and new editor feedback."""
    if not client:
        raise ValueError("Gemini Client not initialized.")
        
    prompt = f"""
    You are a professional book editor. Revise and improve the existing book outline based on the new feedback provided.
    
    Book Title: {title}
    Original Notes: {notes_before}
    Previous Outline:
    {previous_outline}
    
    NEW Editor Feedback (After Review):
    {notes_after}
    
    Instructions:
    - Incorporate the new feedback into the outline.
    - Maintain the overall structure but expand or modify chapters as requested.
    - Ensure Chapter 1 through Final Chapter logical flow.
    - Format as a Markdown list.
    - Return ONLY the improved outline text.
    """
    
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Error regenerating outline with {MODEL_NAME}: {e}")
        raise ValueError(f"Gemini Outline Regeneration Error: {str(e)}")
def regenerate_chapter(title: str, outline_text: str, chapter_number: int, previous_summaries: str, chapter_notes: str, current_chapter_title: str, current_chapter_content: str) -> tuple[str, str]:
    """Regenerates a chapter based on previous draft and editor feedback notes."""
    if not client:
        raise ValueError("Gemini Client not initialized.")
        
    prompt = f"""
    You are a professional book editor. Revise and improve Chapter {chapter_number} of the book titled '{title}'.
    
    The overall outline is:
    {outline_text}
    
    Context from previous chapters:
    {previous_summaries}
    
    NEW Editor Feedback (After Review):
    {chapter_notes}
    
    CURRENT VERSION Chapter Title: {current_chapter_title}
    CURRENT VERSION Chapter Content:
    {current_chapter_content}
    
    Instructions:
    - Revise and improve the chapter based on the editor's feedback notes provided.
    - Preserve narrative continuity and style while incorporating changes.
    - Split the response into a Chapter Title and the full Content, separated by '---CONTENT_START---'.
    
    Example response structure:
    The New Title
    ---CONTENT_START---
    The sun began to set again...
    """
    
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )
        if not response or not hasattr(response, 'text'):
            raise ValueError("No response text from Gemini.")
            
        raw_text = response.text.strip()
        
        if "---CONTENT_START---" in raw_text:
            parts = raw_text.split("---CONTENT_START---")
            chapter_title = parts[0].strip()
            chapter_content = parts[1].strip()
        else:
            chapter_title = current_chapter_title
            chapter_content = raw_text
            
        return chapter_title, chapter_content
    except Exception as e:
        logger.error(f"Error regenerating chapter {chapter_number} with {MODEL_NAME}: {e}")
        raise ValueError(f"Gemini Chapter Regeneration Error ({MODEL_NAME}): {str(e)}")

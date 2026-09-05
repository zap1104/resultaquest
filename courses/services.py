import os
import json
import docx
import pdfplumber
from dotenv import load_dotenv, find_dotenv
from pptx import Presentation
from google import genai
from google.genai import types

# Force Python to find the .env file wherever it is
load_dotenv(find_dotenv())

api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

# Define a single source of truth for the model name
GEMINI_MODEL = "gemini-3.6-flash"


def extract_text_from_file(uploaded_file):
    """
    Extracts text from PPTX, DOCX, TXT, and digital PDFs.
    """
    filename = uploaded_file.name.lower()
    text = ""
    uploaded_file.seek(0)

    try:
        if filename.endswith('.pptx'):
            prs = Presentation(uploaded_file)
            runs = []
            for slide in prs.slides:
                for shape in slide.shapes:
                    if shape.has_text_frame:
                        for p in shape.text_frame.paragraphs:
                            if p.text.strip():
                                runs.append(p.text.strip())
                    if shape.has_table:
                        for row in shape.table.rows:
                            for cell in row.cells:
                                if cell.text.strip():
                                    runs.append(cell.text.strip())
            text = "\n".join(runs)

        elif filename.endswith('.docx'):
            doc = docx.Document(uploaded_file)
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())

        elif filename.endswith('.txt'):
            text = uploaded_file.read().decode('utf-8', errors='ignore')

        elif filename.endswith('.pdf'):
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"

    except Exception as e:
        print(f"[Text Extraction Error]: {e}")

    return text.strip()


def generate_course_journey(course, uploaded_file=None):
    """
    Coordinates curriculum generation via multimodal Gemini or text fallback.
    """
    if client and uploaded_file:
        try:
            return _call_gemini_multimodal(course.title, uploaded_file)
        except Exception as e:
            print(f"[Gemini Multimodal Failure]: {e}")

    # If text was pre-extracted
    raw_text = course.syllabus_text or ""
    if client and len(raw_text) > 40:
        try:
            return _call_gemini_text(course.title, raw_text)
        except Exception as e:
            print(f"[Gemini Text Failure]: {e}")

    print("[Falling back to mock course journey]")
    return _generate_mock_journey(course.title)


def _get_curriculum_prompt(course_title):
    return f"""
    You are an expert university curriculum designer.
    Analyze the provided study material for the course "{course_title}".
    
    Break down this material into 2 to 4 sequential study chapters.
    Each chapter must contain:
    1. A concise, structured "review_content" study guide (2-4 paragraphs).
    2. A 3-to-5 question multiple-choice "quiz" testing comprehension.
    3. Each question must have 4 choices with exactly one "is_correct": true.

    Output MUST adhere strictly to this JSON structure:
    {{
      "chapters": [
        {{
          "title": "Chapter Title",
          "review_content": "Detailed educational summary...",
          "quiz": {{
            "questions": [
              {{
                "text": "Question text here?",
                "choices": [
                  {{"text": "Choice A", "is_correct": false}},
                  {{"text": "Choice B", "is_correct": true}},
                  {{"text": "Choice C", "is_correct": false}},
                  {{"text": "Choice D", "is_correct": false}}
                ]
              }}
            ]
          }}
        }}
      ]
    }}
    """


def _call_gemini_multimodal(course_title, uploaded_file):
    filename = uploaded_file.name.lower()
    uploaded_file.seek(0)
    file_bytes = uploaded_file.read()

    mime_type = None
    if filename.endswith('.pdf'):
        mime_type = 'application/pdf'
    elif filename.endswith('.png'):
        mime_type = 'image/png'
    elif filename.endswith(('.jpg', '.jpeg')):
        mime_type = 'image/jpeg'

    # If it's a format Gemini accepts directly as binary parts
    if mime_type:
        contents = [
            types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
            _get_curriculum_prompt(course_title),
        ]
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )
        return _validate_response(response.text)

    # For PPTX, DOCX, TXT: extract text and send as prompt
    extracted_text = extract_text_from_file(uploaded_file)
    return _call_gemini_text(course_title, extracted_text)


def _call_gemini_text(course_title, text):
    prompt = f"{_get_curriculum_prompt(course_title)}\n\nStudy Material:\n\"\"\"{text[:12000]}\"\"\""
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )
    return _validate_response(response.text)


def _validate_response(raw_json):
    data = json.loads(raw_json)
    if "chapters" in data and isinstance(data["chapters"], list) and len(data["chapters"]) > 0:
        return data
    raise ValueError("Invalid curriculum structure returned by Gemini.")


def _generate_mock_journey(title):
    return {
        "chapters": [
            {
                "title": "Core Subject Overview",
                "review_content": "This chapter introduces fundamental principles. Master these basics before proceeding to specialized applications.",
                "quiz": {
                    "questions": [
                        {
                            "text": "What is the primary objective of this introductory module?",
                            "choices": [
                                {"text": "Establish core theoretical foundations", "is_correct": True},
                                {"text": "Skip directly to final evaluation", "is_correct": False},
                                {"text": "Ignore prerequisite knowledge", "is_correct": False},
                                {"text": "Perform arbitrary calculations", "is_correct": False}
                            ]
                        }
                    ]
                }
            }
        ]
    }
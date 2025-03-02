"""
This module provides functions to interact with the DeepSeek LLM
to enhance a user's resume and calculate an ATS score.
"""

from services.azure_open_ai import get_azure_openai_llm
from models.resume import Resume
import json

def enhance_resume_with_deepseek(resume_data: dict) -> dict:
    """
    Takes the user's resume data as a dict, sends it to the DeepSeek LLM
    to improve phrasing, structure, and provide an ATS score.

    Returns a dict containing the improved resume text (or structured data)
    and an ats_score, e.g.:
    {
      "improved_resume": "...string or JSON resume data...",
      "ats_score": 92
    }
    """
    llm = get_azure_openai_llm()

    # 1. Prepare the prompt:
    prompt_instructions = f"""
You are an AI specialized in enhancing resumes for higher ATS (Applicant Tracking System) scores.
DO NOT provide any chain-of-thought or commentary.

Here is the user's resume data in JSON:
{json.dumps(resume_data, indent=2)}

Transform or refine it into a professional, ATS-friendly resume. 
Return exactly THIS JSON structure (no quotes, no code blocks, no prefix):

{{
  "improved_resume": "final improved text only",
  "ats_score": 0
}}

Where:
  "improved_resume" is the entire improved resume text (plain text),
  "ats_score" is an integer 0-100 indicating ATS friendliness.

No additional keys or text outside these braces. 
Only output valid JSON, and do not place your output in a string.
"""


    # 2. Call the LLM with the instructions
    response = llm.call_as_llm(prompt_instructions)

    # 3. The AI should return JSON with "improved_resume" and "ats_score"
    # But we should safely parse it. If there's an error, fallback.
    try:
         # 1) If the model returns a string that STARTS with a quote or code fence, strip them
        cleaned_response = response.strip()
        
        # Remove triple backticks or code fences if present
        if cleaned_response.startswith("```"):
            cleaned_response = cleaned_response.lstrip("`").strip()
        if cleaned_response.startswith("{") is False:
            # It's not starting with {, let's try to find first { in the text
            start_index = cleaned_response.find("{")
            if start_index != -1:
                cleaned_response = cleaned_response[start_index:]
        
        # Now parse
        output = json.loads(cleaned_response)

        improved_resume = output.get("improved_resume", "")
        ats_score = output.get("ats_score", 0)

        return {
            "improved_resume": improved_resume,
            "ats_score": ats_score
        }
    except Exception as e:
        # fallback if the model didn't comply
        return {
            "improved_resume": response,
            "ats_score": 0
        }
    except json.JSONDecodeError:
        # If the LLM returned non-JSON text, fallback:
        return {
            "improved_resume": response,
            "ats_score": 0
        }

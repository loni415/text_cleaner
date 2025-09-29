# python step3_iter_clean_v3.py my_document.txt

import ollama
import json
import os
import re
import subprocess
import sys
import argparse
from pathlib import Path
from cleaning_functions import extract_body_by_headings, remove_citations, remove_english_abstract

# --- Configuration ---
OLLAMA_MODEL = "llama3:16k" 

# --- Function Library Mapping ---
AVAILABLE_FUNCTIONS = {
    "extract_body_by_headings": extract_body_by_headings,
    "remove_citations": remove_citations,
    "remove_english_abstract": remove_english_abstract,
}

def get_cleaning_parameters(file_content: str, feedback: str = None) -> dict:
    """
    Step 1: LLM analyzes text to extract key parameters for cleaning functions.
    This is more reliable than asking it to generate a complex plan.
    """
    print(f"🤖 Step 1: Analyzing document to extract cleaning parameters with '{OLLAMA_MODEL}'...")
    
    system_prompt = f"""
    You are an expert data cleaning agent. Your task is to analyze a document and extract the necessary parameters to clean it.

    Your goal is to find the information needed to isolate the main narrative body.

    Please provide a simple JSON object with the following keys:
    - "start_heading": The exact text of the heading where the main content begins (e.g., "1 引言").
    - "end_heading": The exact text of the heading where the references or bibliography begins (e.g., "参考文献").
    - "has_citations": A boolean (true/false) indicating if you see citation markers like [1] or [2]34-56.
    - "has_english_abstract": A boolean (true/false) indicating if you see an English abstract at the end.

    Example Response:
    {{
        "start_heading": "# 1 引言",
        "end_heading": "# 参考文献",
        "has_citations": true,
        "has_english_abstract": true
    }}

    Analyze the following text and provide ONLY the JSON object.
    """
    
    user_prompt_content = file_content
    if feedback:
        print(f"   -> Incorporating user feedback: '{feedback}'")
        user_prompt_content = (
            f"The previous attempt was incorrect. User feedback: '{feedback}'.\n\n"
            f"Please create a new, improved JSON parameter object based on this feedback and the content below:\n\n---\n\n{file_content}"
        )
    
    raw_response_content = ""
    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt_content},
            ],
            format="json", options={"temperature": 0.0}
        )
        raw_response_content = response['message']['content']
        
        # Robust JSON parsing
        json_start_index = raw_response_content.find('{')
        if json_start_index != -1:
            json_string = raw_response_content[json_start_index:]
            params = json.loads(json_string)
        else:
            params = None

        print("✅ LLM Parameter Extraction Complete.")
        return params
    except (json.JSONDecodeError, TypeError, IndexError):
        print("❌ Error: LLM did not return a valid JSON object.")
        print(f"   -> LLM Raw Response was:\n---------------------------\n{raw_response_content}\n---------------------------")
        return None
    except Exception as e:
        print(f"❌ An unexpected error occurred during LLM analysis: {e}")
        return None

def execute_cleaning(params: dict, input_file: str, output_file: str):
    """
    Step 2 & 3: Python uses the LLM's parameters to execute a cleaning plan.
    """
    print(f"🚀 Step 2 & 3: Executing cleaning plan based on LLM parameters...")
    
    try:
        text = Path(input_file).read_text(encoding="utf-8")
        
        # 1. Extract main body
        start = params.get("start_heading")
        end = params.get("end_heading")
        if start and end:
            text = extract_body_by_headings(text, start_heading=start, end_heading=end)
        else:
            print("   -> WARNING: Start or end heading not found in LLM params. Skipping body extraction.")

        # 2. Remove citations if detected
        if params.get("has_citations", False):
            text = remove_citations(text)
        
        # 3. Remove English abstract if detected
        if params.get("has_english_abstract", False):
            text = remove_english_abstract(text)

        Path(output_file).write_text(text, encoding="utf-8")
        print(f"✅ Plan executed. Cleaned file saved to '{output_file}'")

    except Exception as e:
        print(f"❌ An error occurred during plan execution: {e}")

def main():
    """
    Orchestrates the entire iterative cleaning process.
    """
    parser = argparse.ArgumentParser(description="Iterative document cleaning with LLM feedback")
    parser.add_argument("input_file", nargs='?', default="Zhang_2022_zh.txt", 
                       help="Path to the input file to clean")
    
    args = parser.parse_args()
    input_file = Path(args.input_file)
    
    if not input_file.exists():
        print(f"❌ Input file not found: {input_file}")
        return

    current_file_to_clean = input_file
    iteration = 1
    feedback = None 
    
    while True:
        print(f"\n--- Starting Cleaning Iteration {iteration} ---")
        cleaned_file = current_file_to_clean.with_name(f"{input_file.stem}_cleaned_v{iteration}.md")

        try:
            content = current_file_to_clean.read_text(encoding="utf-8")
        except Exception as e:
            print(f"❌ Could not read file {current_file_to_clean}: {e}")
            break

        params = get_cleaning_parameters(content, feedback=feedback)
        
        if not params or not isinstance(params, dict):
            print("🛑 No valid cleaning parameters proposed by LLM. Stopping.")
            # Let's see what the LLM proposed before stopping
            print("Final proposed params:", params)
            break
            
        execute_cleaning(params, str(current_file_to_clean), str(cleaned_file))
        
        print(f"🧐 Step 4: Please inspect the cleaned file: {cleaned_file}")
        
        while True:
            approve = input("   -> Approve this version? (y/n): ").lower().strip()
            if approve in ['y', 'n']:
                break
            print("   -> Invalid input. Please enter 'y' or 'n'.")
        
        if approve == 'y':
            print(f"\n🎉 Cleaning complete and approved! Final file: {cleaned_file}")
            break
        else:
            print("   -> Not approved.")
            feedback = input("   -> Please provide a hint for the next attempt: ")
            current_file_to_clean = cleaned_file
            iteration += 1

if __name__ == "__main__":
    main()

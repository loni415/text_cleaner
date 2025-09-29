import os
import ollama
import json
import re
import argparse
from tqdm import tqdm
from pathlib import Path

# --- CONFIGURATION ---
MODEL_NAME = "llama3.1:8b-instruct-fp16"

# --- PROMPT ENGINEERING ---
PRUNING_PROMPT_TEMPLATE = """
You are an expert document analyst. Your task is to identify the start and end of the main narrative content in a document.
Analyze the provided text, which is a list of paragraphs from an academic paper.
Your goal is to find the exact heading or phrase that marks the beginning of the introduction and the exact heading that marks the beginning of the references/bibliography.

Provide your response as a single, valid JSON object with two keys:
- "start_heading": The full, exact text of the heading where the main content begins (e.g., "1 Introduction", "1 引言").
- "end_heading": The full, exact text of the heading where the references or bibliography begins (e.g., "References", "参考文献").

If you cannot find a clear start or end heading, leave the corresponding value as an empty string.

<example>
Text:
...
some preamble...
1 Introduction
This is the first sentence.
...
This is the last sentence.
References
[1] Author, A. (2023).
...

JSON:
{{
    "start_heading": "1 Introduction",
    "end_heading": "References"
}}
</example>

Now, analyze this document's paragraphs:
<document_paragraphs>
{paragraph_list}
</document_paragraphs>

Provide only the raw JSON object as your response.
"""

def get_pruning_parameters(client: ollama.Client, paragraphs: list) -> dict:
    """
    Uses an LLM to find the start and end headings for the main document body.
    """
    # For efficiency, we only send the first and last N paragraphs to the LLM
    # as this is where the relevant headings are most likely to be.
    SAMPLE_SIZE = 20
    head = paragraphs[:SAMPLE_SIZE]
    tail = paragraphs[-SAMPLE_SIZE:]

    # Use a separator to make it clear to the LLM where the document's start and end are.
    paragraph_text_for_llm = "\n".join(head) + "\n\n...[DOCUMENT TRUNCATED]...\n\n" + "\n".join(tail)

    prompt = PRUNING_PROMPT_TEMPLATE.format(paragraph_list=paragraph_text_for_llm)

    try:
        response = client.chat(
            model=MODEL_NAME,
            messages=[{'role': 'user', 'content': prompt}],
            format='json'
        )
        params = json.loads(response['message']['content'])

        # Validate the output from the LLM
        if isinstance(params, dict) and "start_heading" in params and "end_heading" in params:
            return params
        else:
            print(f"  - WARNING: LLM returned malformed JSON. Skipping pruning. Response: {params}")
            return None

    except Exception as e:
        print(f"  - WARNING: LLM analysis for pruning failed: {e}. Skipping pruning.")
        return None

def prune_text_body(text: str, params: dict) -> str:
    """
    Extracts the main body of text between a start and an end heading using regex.
    """
    start_heading = params.get("start_heading")
    end_heading = params.get("end_heading")

    # If headings are missing or empty, return the original text
    if not start_heading or not end_heading:
        print("  - INFO: No valid start/end headings found by LLM. Skipping pruning.")
        return text

    # Escape special regex characters in the headings to ensure they are treated as literals
    start_pattern = re.escape(start_heading)
    end_pattern = re.escape(end_heading)

    # Use regex to find the content between the start and end patterns. re.DOTALL allows '.' to match newlines.
    match = re.search(f"{start_pattern}(.*?){end_pattern}", text, re.DOTALL)

    if match:
        print(f"  - SUCCESS: Extracted main body between '{start_heading}' and '{end_heading}'.")
        return match.group(1).strip()
    else:
        print(f"  - WARNING: Could not find the specified start/end headings in the text. Skipping pruning.")
        return text

def process_directory(input_dir: str, output_dir: str):
    """
    Processes all .txt files from the sentence parsing step.
    """
    if not os.path.isdir(input_dir):
        print(f"Error: Input directory not found at {input_dir}")
        return

    os.makedirs(output_dir, exist_ok=True)

    filenames = sorted([f for f in os.listdir(input_dir) if f.endswith(".txt")])
    if not filenames:
        print(f"No .txt files found in {input_dir}")
        return

    client = ollama.Client()
    print(f"--- Found {len(filenames)} files. Starting Step 4: LLM Pruning with model '{MODEL_NAME}'... ---")

    for filename in tqdm(filenames, desc="Pruning files"):
        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, filename)

        try:
            full_text = Path(input_path).read_text(encoding="utf-8")
            paragraphs = [p.strip() for p in full_text.split('\n\n') if p.strip()]

            if len(paragraphs) < (2 * 5): # If document is too short, skip pruning
                tqdm.write(f"  - Skipping pruning for short document: {filename}")
                pruned_text = full_text
            else:
                pruning_params = get_pruning_parameters(client, paragraphs)
                if pruning_params:
                    pruned_text = prune_text_body(full_text, pruning_params)
                else:
                    pruned_text = full_text # Fallback to full text if LLM fails

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(pruned_text)

        except Exception as e:
            print(f"\nCould not process {filename}. Error: {e}")

    print(f"\n--- Step 4: LLM pruning complete. Pruned files are in {output_dir} ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Step 4: LLM-based pruning to extract the main narrative content.")
    parser.add_argument("input_dir", help="Directory containing parsed .txt files from Step 3.")
    parser.add_argument("output_dir", help="Directory where the pruned .txt files will be saved.")
    args = parser.parse_args()

    process_directory(args.input_dir, args.output_dir)
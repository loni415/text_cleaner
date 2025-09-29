# python stage3_llm_refiner.py ./cleaned_text_stage2 ./cleaned_text_stage3

import os
import ollama
import json
import argparse
from tqdm import tqdm
import traceback

print("--- Running stage3_llm_refiner.py v5.0 (FINAL FIX) ---")

# --- CONFIGURATION ---
MODEL_NAME = "llama3.1:8b-instruct-fp16"  # Or your preferred, capable Ollama model
SCORE_THRESHOLD = 7              # Chunks scoring below this will be sent for repair.
CHUNK_SIZE = 5                   # Number of paragraphs per chunk.
CHUNK_OVERLAP = 1                # Number of paragraphs to overlap between chunks.

# --- PROMPT ENGINEERING (CORRECTED) ---

# The curly braces in the example JSON are now escaped by doubling them up ({{ and }})
CLASSIFIER_PROMPT_TEMPLATE = """
You are a meticulous text quality analyst. Your task is to evaluate a text segment for signs of poor PDF-to-text conversion.
Analyze the following text for structural errors like incorrectly broken sentences, merged paragraphs, or nonsensical line breaks.
Do not evaluate the factual content. Focus ONLY on structure, grammar, and logical flow.

Think step-by-step:
1. Read the text carefully. Does it flow naturally?
2. Are there any sentences that seem to end abruptly without punctuation?
3. Are there paragraphs that seem to be a mashup of two different topics?
4. Is the grammar coherent?

After your analysis, provide your response as a single, valid JSON object with two keys:
- "score": An integer from 1 (very broken) to 10 (perfectly structured).
- "reason": A brief, one-sentence explanation for your score.
The "score" key is mandatory and must always be present.

<example_good>
Text: "The study concluded that further research was necessary. Participants were recruited from a local university."
JSON: {{"score": 10, "reason": "The text is well-structured with complete sentences."}}
</example_good>

<example_bad>
Text: "The study concluded that further. Research was necessary participants were recruited from a local university."
JSON: {{"score": 3, "reason": "A sentence is incorrectly broken after 'further' and improperly merged with the next thought."}}
</example_bad>

Now, evaluate this text:
<text_to_analyze>
{text_chunk}
</text_to_analyze>

Provide only the raw JSON object as your response.
"""

REPAIR_PROMPT_TEMPLATE = """
You are an expert text editor. You will be given a piece of text that was flagged for a specific structural error resulting from a bad PDF conversion.
Your task is to fix ONLY the identified problem and return the corrected text.

**CRITICAL RULES:**
1.  Correct the specific error described in the 'Reason for flagging'.
2.  Do NOT add any new information, content, or commentary.
3.  Do NOT change the meaning of the text.
4.  Preserve the original paragraph structure as best as possible.
5.  Return only the corrected text, with no preamble or explanation.

**Reason for flagging:** {reason}

**Problematic Text:**
<text_to_fix>
{text_chunk}
</text_to_fix>

**Corrected Text:**
"""

def classify_chunk(client: ollama.Client, text_chunk: str) -> dict:
    """
    "Bulletproof" version: Uses the LLM to score a text chunk and gracefully
    handles any malformed or incomplete response from the LLM.
    """
    # This line will now execute correctly.
    prompt = CLASSIFIER_PROMPT_TEMPLATE.format(text_chunk=text_chunk)
    try:
        response = client.chat(
            model=MODEL_NAME,
            messages=[{'role': 'user', 'content': prompt}],
            format='json'
        )
        result = json.loads(response['message']['content'])
        
        score = result.get('score')
        reason = result.get('reason')

        if score is not None and reason is not None:
            try:
                score_value = int(score)
                return {"score": score_value, "reason": str(reason)}
            except (ValueError, TypeError):
                print(f"Debug: LLM returned non-integer score: '{score}'. Defaulting to 1.")
                return {"score": 1, "reason": f"LLM returned non-integer score: '{score}'"}
        else:
            print(f"Debug: LLM JSON missing keys. Response: {result}. Defaulting to 1.")
            return {"score": 1, "reason": f"LLM response missing keys: {result}"}
        
    except Exception as e:
        print(f"  - Classification error: {e}. Defaulting to 1.")
        return {"score": 1, "reason": f"Error during classification: {e}"}

def repair_chunk(client: ollama.Client, text_chunk: str, reason: str) -> str:
    """Uses the LLM to repair a text chunk."""
    prompt = REPAIR_PROMPT_TEMPLATE.format(text_chunk=text_chunk, reason=reason)
    try:
        response = client.chat(
            model=MODEL_NAME,
            messages=[{'role': 'user', 'content': prompt}]
        )
        return response['message']['content'].strip()
    except Exception as e:
        print(f"  - Repair failed for chunk: {e}. Returning original.")
        return text_chunk

def process_file(client: ollama.Client, file_path: str) -> str:
    """Reads, chunks, classifies, repairs, and reassembles a single file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()

    paragraphs = text.split('\n\n')
    if len(paragraphs) <= CHUNK_SIZE:
        chunks = ["\n\n".join(paragraphs)]
    else:
        chunks = []
        for i in range(0, len(paragraphs), CHUNK_SIZE - CHUNK_OVERLAP):
            chunk = "\n\n".join(paragraphs[i:i + CHUNK_SIZE])
            chunks.append(chunk)

    repaired_chunks = []
    print(f"\nProcessing {os.path.basename(file_path)} in {len(chunks)} chunks...")
    
    for chunk in tqdm(chunks, desc="  - Analyzing chunks", leave=False):
        classification = classify_chunk(client, chunk)
        score = classification.get('score', 1)
        reason = classification.get('reason', 'Unknown error')
        
        if score < SCORE_THRESHOLD:
            repaired_chunk = repair_chunk(client, chunk, reason)
            repaired_chunks.append(repaired_chunk)
        else:
            repaired_chunks.append(chunk)

    full_text = "\n\n".join(repaired_chunks)
    final_paragraphs = []
    seen_paragraphs = set()
    for para in full_text.split('\n\n'):
        para_strip = para.strip()
        if para_strip and para_strip not in seen_paragraphs:
            final_paragraphs.append(para.strip())
            seen_paragraphs.add(para_strip)
            
    return "\n\n".join(final_paragraphs)

def process_directory(input_dir: str, output_dir: str):
    """Processes all .txt files from the Stage 2 output directory."""
    if not os.path.isdir(input_dir):
        print(f"Error: Input directory not found at {input_dir}")
        return

    os.makedirs(output_dir, exist_ok=True)
    
    filenames = sorted([f for f in os.listdir(input_dir) if f.endswith(".txt")])
    if not filenames:
        print(f"No .txt files found in {input_dir}")
        return

    client = ollama.Client()
    print(f"Starting Stage 3 LLM refinement with model: {MODEL_NAME}")

    for filename in filenames:
        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, filename)
        
        try:
            final_text = process_file(client, input_path)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(final_text)
        except Exception as e:
            print(f"\n--- FATAL ERROR PROCESSING {filename} ---")
            print(f"An unexpected error occurred: {e}")
            print("Full traceback:")
            traceback.print_exc()
            print("------------------------------------------")
    
    print("\nStage 3 refinement complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 3: LLM-based text refinement using a classify-then-repair workflow.")
    parser.add_argument("input_dir", help="Directory containing cleaned .txt files from Stage 2.")
    parser.add_argument("output_dir", help="Directory where the Stage 3 refined files will be saved.")
    args = parser.parse_args()
    
    process_directory(args.input_dir, args.output_dir)
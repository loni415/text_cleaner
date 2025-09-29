import os
import json
from tqdm import tqdm
import ftfy
import ollama

# --- CONFIGURATION ---
INTERMEDIATE_DIRECTORY = "llm_iterative/cleaned_files/intermediate_json"
FINAL_OUTPUT_DIRECTORY = "llm_iterative/cleaned_files/final_llm_polished"
OLLAMA_REVIEW_MODEL = "llama3.1:8b-instruct-fp16"
ENABLE_LLM_REVIEW = True

# --- HELPER FUNCTION ---
def llm_polish_and_validate(paragraph: str) -> str:
    # (This function is unchanged)
    system_prompt = (
        "You are an expert text-cleaning AI. Your task is to review a paragraph extracted from an academic PDF. "
        "1. Correct any grammatical errors, fix broken or merged sentences, and ensure it reads as a single, coherent paragraph. "
        "2. DO NOT change the original meaning, facts, or add any new information. Preserve the original language and tone. "
        "3. If the input text is not a coherent paragraph (e.g., it is a list of citations, a document header, a table fragment, or complete gibberish), you MUST reply with only the single word: JUNK. "
        "4. Otherwise, return only the cleaned paragraph text."
    )
    prompt = f"Please review and clean the following text:\n\n---\n\n{paragraph}"
    try:
        response = ollama.chat(
            model=OLLAMA_REVIEW_MODEL,
            messages=[{'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': prompt}],
            options={"temperature": 0.0}
        )
        cleaned_text = response['message']['content'].strip()
        if cleaned_text.upper() == "JUNK":
            return None
        return cleaned_text
    except Exception as e:
        tqdm.write(f"  - Ollama API Error (Review): {e}")
        return paragraph

# --- MAIN EXECUTION ---
def main():
    if not os.path.isdir(INTERMEDIATE_DIRECTORY):
        print(f"❌ ERROR: Intermediate directory not found at '{INTERMEDIATE_DIRECTORY}'")
        print("Please run 'step1_preprocess_batch.py' first.")
        return

    os.makedirs(FINAL_OUTPUT_DIRECTORY, exist_ok=True)
    json_files = [f for f in os.listdir(INTERMEDIATE_DIRECTORY) if f.endswith('.json')]
    print(f"--- Found {len(json_files)} JSON files to review with LLM. ---")

    for json_file in tqdm(json_files, desc="Processing all JSON files"):
        base_name = os.path.splitext(json_file)[0]
        input_path = os.path.join(INTERMEDIATE_DIRECTORY, json_file)
        output_path = os.path.join(FINAL_OUTPUT_DIRECTORY, f"{base_name}.txt")

        if os.path.exists(output_path):
            tqdm.write(f"  - Skipping '{base_name}', final text file already exists.")
            continue

        with open(input_path, 'r', encoding='utf-8') as f:
            reconstructed_paragraphs = json.load(f)
        
        tqdm.write(f"\n-> Reviewing {len(reconstructed_paragraphs)} paragraphs from '{base_name}'...")
        
        if ENABLE_LLM_REVIEW:
            llm_polished_paragraphs = []
            for para in tqdm(reconstructed_paragraphs, desc=f"LLM Review ({base_name})", leave=False):
                polished_para = llm_polish_and_validate(para)
                if polished_para:
                    llm_polished_paragraphs.append(polished_para)
            final_text = "\n\n".join(llm_polished_paragraphs)
        else:
            final_text = "\n\n".join(reconstructed_paragraphs)

        final_text = ftfy.fix_text(final_text)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_text)
            
        tqdm.write(f"  - ✅ Saved final polished text for '{base_name}' to: {output_path}")

    print("\n--- LLM Review complete for all files. ---")

if __name__ == "__main__":
    main()
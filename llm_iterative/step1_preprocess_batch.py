import os
import re
from tqdm import tqdm
import json

# Import the universal partition function
from unstructured.partition.auto import partition

# --- CONFIGURATION ---

# 1. <<< ACTION REQUIRED: UPDATE YOUR DIRECTORY PATHS HERE >>>
# Directory containing your source .pdf, .md, and .txt files
SOURCE_DIRECTORY = "/Users/lukasfiller/dev/unstructured/iterative_cleaner_8sep/llm_iterative/source_files"
# Directory where the intermediate, rule-based cleaned paragraphs will be saved
INTERMEDIATE_DIRECTORY = "/Users/lukasfiller/dev/unstructured/iterative_cleaner_8sep/llm_iterative/cleaned_files/intermediate_json"

# --- HELPER FUNCTIONS ---

def find_supported_files(directory: str) -> list:
    """Finds all supported files (.pdf, .txt, .md, .docx) in a directory."""
    supported_files = []
    supported_extensions = ['.pdf', '.md', '.txt', '.docx']
    print(f"--- Scanning for supported files in: {directory} ---")
    for root, _, files in os.walk(directory):
        for file in files:
            if not file.startswith('.') and any(file.lower().endswith(ext) for ext in supported_extensions):
                supported_files.append(os.path.join(root, file))
    return supported_files

def extract_elements(file_path: str) -> list:
    """
    Uses the universal `partition` function to extract text elements,
    automatically handling PDF, MD, and TXT files.
    """
    print(f"\n-> Processing file with unstructured: {os.path.basename(file_path)}")
    try:
        # This is the key change: partition() auto-detects the file type.
        elements = partition(
            filename=file_path,
            strategy="hi_res",  # 'hi_res' is great for PDFs, and harmless for TXT/MD
            languages=["eng", "chi_sim"]
        )
        return [el.text for el in elements if el.text and el.text.strip()]
    except Exception as e:
        print(f"  - ERROR: Could not process file with unstructured. Reason: {e}")
        return None

def reconstruct_and_polish_rules_only(elements: list) -> list:
    """
    Filters junk, then intelligently reconstructs paragraphs using rule-based logic.
    """
    junk_patterns = re.compile(
        r'^(Vol\.\s*\d+|Journal\s*of|Jun\.\s*\d{4}|第\s*\d+\s*卷|武汉交通职业学院学报|Copyright|http:|www\.cnki\.net|'
        r'摘要:|关键词:|中图分类号:|DOI:|文章编号:|开放科学|收稿日期:|作者简介:|参考文献:|'
        r'\(责任编辑:.*\)|'
        r'-\s*\d+\s*-|'
        r'\[\d+\]|'
        r'张雯:习近平总体国家安全观的思想理论渊源)',
        re.IGNORECASE
    )
    
    filtered_elements = [el for el in elements if not junk_patterns.search(el.strip())]

    reconstructed_paragraphs = []
    current_paragraph = ""
    sentence_enders = tuple(['。', '！', '？', '”', '.'])

    for text in filtered_elements:
        clean_text = re.sub(r'([\u4e00-\u9fff])\s+([\u4e00-\u9fff])', r'\1\2', text).strip()
        if not clean_text:
            continue
        current_paragraph += " " + clean_text
        if clean_text.endswith(sentence_enders):
            reconstructed_paragraphs.append(current_paragraph.strip())
            current_paragraph = ""
            
    if current_paragraph:
        reconstructed_paragraphs.append(current_paragraph.strip())

    final_paragraphs = [p for p in reconstructed_paragraphs if len(p) > 50]
    return final_paragraphs

# --- MAIN EXECUTION ---
def main():
    if not os.path.isdir(SOURCE_DIRECTORY):
        print(f"❌ ERROR: Source directory not found at '{SOURCE_DIRECTORY}'")
        return

    os.makedirs(INTERMEDIATE_DIRECTORY, exist_ok=True)
    all_files = find_supported_files(SOURCE_DIRECTORY)
    print(f"--- Found {len(all_files)} supported files to process. ---")

    for file_path in tqdm(all_files, desc="Processing all files"):
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_path = os.path.join(INTERMEDIATE_DIRECTORY, f"{base_name}.json")

        if os.path.exists(output_path):
            tqdm.write(f"  - Skipping '{base_name}', intermediate file already exists.")
            continue

        elements = extract_elements(file_path)
        if not elements:
            tqdm.write(f"  - No content extracted from '{base_name}'. Skipping.")
            continue
        
        reconstructed_paragraphs = reconstruct_and_polish_rules_only(elements)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(reconstructed_paragraphs, f, indent=2, ensure_ascii=False)
            
        tqdm.write(f"  - ✅ Saved {len(reconstructed_paragraphs)} paragraphs from '{base_name}' to intermediate JSON.")

    print("\n--- Preprocessing complete for all files. ---")

if __name__ == "__main__":
    main()
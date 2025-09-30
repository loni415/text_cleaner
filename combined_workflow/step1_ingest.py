import os
import argparse
from tqdm import tqdm
#from unstructured.partition.api import partition_via_api
from unstructured.partition.auto import partition

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

def extract_text_from_file(file_path: str) -> str:
    """
    Uses the universal `partition` function to extract text elements,
    automatically handling PDF, MD, and TXT files.
    """
    print(f"\n-> Processing file with unstructured: {os.path.basename(file_path)}")
    try:
        elements = partition(
            filename=file_path,
            strategy="hi_res",
            languages=["eng", "chi_sim"]
        )
        return "\n\n".join([el.text for el in elements if el.text and el.text.strip()])
    except Exception as e:
        print(f"  - ERROR: Could not process file with unstructured. Reason: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Step 1: Ingest and extract raw text from various document formats.")
    parser.add_argument("source_dir", help="Directory containing source .pdf, .md, .txt, and .docx files.")
    parser.add_argument("output_dir", help="Directory where the extracted raw .txt files will be saved.")
    args = parser.parse_args()

    if not os.path.isdir(args.source_dir):
        print(f"❌ ERROR: Source directory not found at '{args.source_dir}'")
        return

    os.makedirs(args.output_dir, exist_ok=True)
    all_files = find_supported_files(args.source_dir)
    print(f"--- Found {len(all_files)} supported files to process. ---")

    for file_path in tqdm(all_files, desc="Ingesting files"):
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_path = os.path.join(args.output_dir, f"{base_name}.txt")

        if os.path.exists(output_path):
            tqdm.write(f"  - Skipping '{base_name}', output file already exists.")
            continue

        raw_text = extract_text_from_file(file_path)
        if not raw_text:
            tqdm.write(f"  - No content extracted from '{base_name}'. Skipping.")
            continue

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(raw_text)

        tqdm.write(f"  - ✅ Saved extracted text from '{base_name}' to a .txt file.")

    print("\n--- Step 1: Ingestion complete for all files. ---")

if __name__ == "__main__":
    main()
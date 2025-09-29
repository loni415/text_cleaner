# python stage1_cleaner.py ./raw_text ./cleaned_text_stage1

import os
import re
import argparse
from tqdm import tqdm

# --- CUSTOMIZED & COMPILED REGEX PATTERNS (CORRECTED) ---

# Matches common academic headers/footers, now customized for your specific document.
HEADER_FOOTER_PATTERNS = re.compile(
    r'^('
    # Matches standalone page numbers (e.g., "1", "2", "23 24")
    r'\s*(\d+\s*)+\s*$|'
    # Matches Table of Contents lines with dot leaders (e.g., "Chapter 1 .......... 5")
    r'.*?\.{2,}\s*\d+\s*$|'
    # Matches entire lines that are likely just footnote text (e.g., "① Cheng,M.,&Zhao,X.(2020)...")
    r'\s*①.*$|'
    # Original generic patterns (still useful!)
    r'Page \d+ of \d+\s*$|'
    # CORRECTED LINE: Removed the redundant and misplaced (?i) flag
    r'(journal of|proceedings of|transactions on|review of|advances in) .*|'
    r'https?://[^\s]+|'
    r'\b\d{4}\s*–\s*\d{4}\b|'
    r'\bdoi:[^\s]+'
    r')',
    re.IGNORECASE | re.MULTILINE
)

# New pattern to fix duplicated phrases like "Foreword Foreword" -> "Foreword"
DUPLICATE_PHRASE_PATTERN = re.compile(r'\b(.+?)\b\s+\1\b')

# New pattern to remove any remaining inline footnote markers
INLINE_FOOTNOTE_PATTERN = re.compile(r'[①]')

# Matches a word split by a hyphen at the end of a line. e.g., "experi-\nment"
DEHYPHENATE_PATTERN = re.compile(r'([a-zA-Z])-\n([a-zA-Z])')

# Matches and removes line numbers at the start of a line (e.g., "12 | text...")
LINE_NUMBER_PATTERN = re.compile(r'^\s*\d+\s*\|?\s*')

# Matches potential list item markers (e.g., a., b., 1., i.) to prevent incorrect joining
LIST_ITEM_PATTERN = re.compile(r'^\s*(\([a-zA-Z0-9]+\)|[a-zA-Z0-9]\.|[•●*–-]\s)')

# Matches common figure/table captions to isolate them
CAPTION_PATTERN = re.compile(r'^(Fig(ure)?\.? \d+|Table \d+)\b.*$', re.IGNORECASE | re.MULTILINE)

# Normalization for whitespace
MULTI_WHITESPACE_PATTERN = re.compile(r'[ \t]+')
MULTI_NEWLINE_PATTERN = re.compile(r'\n{3,}')


def clean_academic_text(text: str) -> str:
    """
    Applies a series of rule-based cleaning steps to text extracted from academic PDFs.
    The order of operations is important.
    """
    # 1. Remove identified headers, footers, page numbers, and ToC lines.
    cleaned_text = HEADER_FOOTER_PATTERNS.sub('', text)

    # 2. Fix duplicated phrases (e.g., "Foreword Foreword" -> "Foreword").
    cleaned_text = DUPLICATE_PHRASE_PATTERN.sub(r'\1', cleaned_text)

    # 3. Remove any remaining inline footnote markers.
    cleaned_text = INLINE_FOOTNOTE_PATTERN.sub('', cleaned_text)

    # 4. Remove line numbers from the start of lines.
    cleaned_text = LINE_NUMBER_PATTERN.sub('', cleaned_text)

    # 5. Re-join words that were hyphenated across lines.
    cleaned_text = DEHYPHENATE_PATTERN.sub(r'\1\2', cleaned_text)
    
    # 6. Join broken sentences and paragraphs (procedural step).
    lines = cleaned_text.split('\n')
    rejoined_lines = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            rejoined_lines.append('') # Preserve paragraph breaks
            i += 1
            continue

        is_complete_thought = line.endswith(('.', '?', '!', '"', '”', ':')) or \
                              LIST_ITEM_PATTERN.match(line) or \
                              CAPTION_PATTERN.match(line)
        
        if not is_complete_thought and (i + 1) < len(lines):
            next_line = lines[i+1].strip()
            if next_line and not LIST_ITEM_PATTERN.match(next_line):
                lines[i+1] = line + ' ' + next_line
            else:
                rejoined_lines.append(line)
        else:
            rejoined_lines.append(line)
        i += 1
    cleaned_text = '\n'.join(rejoined_lines)

    # 7. Normalize whitespace.
    cleaned_text = MULTI_WHITESPACE_PATTERN.sub(' ', cleaned_text)
    cleaned_text = MULTI_NEWLINE_PATTERN.sub('\n\n', cleaned_text)
    
    return cleaned_text.strip()


def process_directory(input_dir: str, output_dir: str):
    """
    Processes all .txt files in the input directory and saves cleaned versions.
    """
    if not os.path.isdir(input_dir):
        print(f"Error: Input directory not found at {input_dir}")
        return

    os.makedirs(output_dir, exist_ok=True)
    
    filenames = sorted([f for f in os.listdir(input_dir) if f.endswith(".txt")])
    
    if not filenames:
        print(f"No .txt files found in {input_dir}")
        return

    print(f"Found {len(filenames)} .txt files. Starting cleaning process...")
    
    for filename in tqdm(filenames, desc="Cleaning files"):
        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, filename)
        
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                raw_text = f.read()
            
            cleaned_text = clean_academic_text(raw_text)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_text)
        except Exception as e:
            print(f"\nCould not process {filename}. Error: {e}")

    print(f"\nCleaning complete. Cleaned files are in {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="A rule-based cleaner for text extracted from academic PDFs.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "input_dir", 
        help="Directory containing the raw .txt files."
    )
    parser.add_argument(
        "output_dir", 
        help="Directory where the cleaned .txt files will be saved."
    )
    args = parser.parse_args()
    
    process_directory(args.input_dir, args.output_dir)
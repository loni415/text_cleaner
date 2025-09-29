import os
import re
import argparse
from tqdm import tqdm

# --- CUSTOMIZED & COMPILED REGEX PATTERNS ---
# This set of patterns is a combination of the most effective rules from both original workflows.

# Matches common academic headers/footers, page numbers, ToC lines, and other artifacts.
HEADER_FOOTER_PATTERNS = re.compile(
    r'^('
    # Standalone page numbers
    r'\s*(\d+\s*)+\s*$|'
    # Table of Contents lines with dot leaders
    r'.*?\.{2,}\s*\d+\s*$|'
    # Common academic phrases, journal names, etc.
    r'(journal of|proceedings of|transactions on|review of|advances in) .*|'
    # URLs
    r'https?://[^\s]+|'
    # DOI links
    r'\bdoi:[^\s]+|'
    # Copyright notices
    r'©.*|'
    # Common Chinese academic headers
    r'第\s*\d+\s*卷|武汉交通职业学院学报|摘要:|关键词:|中图分类号:|文章编号:|收稿日期:|作者简介:|参考文献:|'
    # Common English academic headers
    r'Abstract:|Keywords:|DOI:|Article ID:|Received:|Biography:'
    r')',
    re.IGNORECASE | re.MULTILINE
)

# Fixes duplicated phrases (e.g., "Foreword Foreword" -> "Foreword")
DUPLICATE_PHRASE_PATTERN = re.compile(r'\b(.+?)\b\s+\1\b')

# Removes inline footnote/citation markers (e.g., [1], [2], [①])
INLINE_CITATION_PATTERN = re.compile(r'\[\s*\d+\s*\]|\[[①②③④⑤⑥⑦⑧⑨⑩]\]')

# Re-joins words hyphenated across lines (e.g., "experi-\nment" -> "experiment")
DEHYPHENATE_PATTERN = re.compile(r'([a-zA-Z])-\n([a-zA-Z])')

# Removes line numbers at the start of a line (e.g., "12 | text...")
LINE_NUMBER_PATTERN = re.compile(r'^\s*\d+\s*\|?\s*')

# Matches potential list item markers to prevent incorrect paragraph joining
LIST_ITEM_PATTERN = re.compile(r'^\s*(\([a-zA-Z0-9]+\)|[a-zA-Z0-9][\.\)]|[•●*–-]\s)')

# Matches common figure/table captions to isolate them
CAPTION_PATTERN = re.compile(r'^(Fig(ure)?\.? \d+|Table \d+|图\s*\d+|表\s*\d+)\b.*$', re.IGNORECASE | re.MULTILINE)

# Normalizes whitespace for consistency
MULTI_WHITESPACE_PATTERN = re.compile(r'[ \t]+')
MULTI_NEWLINE_PATTERN = re.compile(r'\n{3,}')


def clean_text_with_rules(text: str) -> str:
    """
    Applies a series of rule-based cleaning steps to raw text.
    The order of operations is important for best results.
    """
    # 1. Remove major artifacts like headers and footers.
    cleaned_text = HEADER_FOOTER_PATTERNS.sub('', text)

    # 2. Fix duplicated phrases.
    cleaned_text = DUPLICATE_PHRASE_PATTERN.sub(r'\1', cleaned_text)

    # 3. Remove inline citation markers.
    cleaned_text = INLINE_CITATION_PATTERN.sub('', cleaned_text)

    # 4. Remove starting line numbers.
    cleaned_text = LINE_NUMBER_PATTERN.sub('', cleaned_text)

    # 5. Re-join hyphenated words.
    cleaned_text = DEHYPHENATE_PATTERN.sub(r'\1\2', cleaned_text)

    # 6. Intelligently join broken sentences and paragraphs.
    lines = cleaned_text.split('\n')
    rejoined_lines = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            rejoined_lines.append('') # Preserve paragraph breaks
            i += 1
            continue

        # A line is considered a "complete thought" if it ends with punctuation or is a list/caption.
        is_complete_thought = line.endswith(('.', '?', '!', '"', '”', '。', '？', '！', ':')) or \
                              LIST_ITEM_PATTERN.match(line) or \
                              CAPTION_PATTERN.match(line)

        # If the line is not a complete thought, and the next line exists and is not a list item, merge them.
        if not is_complete_thought and (i + 1) < len(lines):
            next_line = lines[i+1].strip()
            if next_line and not LIST_ITEM_PATTERN.match(next_line):
                lines[i+1] = line + ' ' + next_line # Prepend current line to the next
            else:
                rejoined_lines.append(line)
        else:
            rejoined_lines.append(line)
        i += 1
    cleaned_text = '\n'.join(rejoined_lines)

    # 7. Normalize all whitespace for a clean final output.
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

    print(f"--- Found {len(filenames)} .txt files. Starting Step 2: Rule-based cleaning... ---")

    for filename in tqdm(filenames, desc="Cleaning files"):
        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, filename)

        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                raw_text = f.read()

            cleaned_text = clean_text_with_rules(raw_text)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_text)
        except Exception as e:
            print(f"\nCould not process {filename}. Error: {e}")

    print(f"\n--- Step 2: Rule-based cleaning complete. Cleaned files are in {output_dir} ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Step 2: A rule-based cleaner for text extracted from documents.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "input_dir",
        help="Directory containing the raw .txt files from Step 1."
    )
    parser.add_argument(
        "output_dir",
        help="Directory where the rule-cleaned .txt files will be saved."
    )
    args = parser.parse_args()

    process_directory(args.input_dir, args.output_dir)
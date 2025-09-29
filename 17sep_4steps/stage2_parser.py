# python stage2_parser.py ./cleaned_text_stage1 ./cleaned_text_stage2

import os
import spacy
import argparse
from tqdm import tqdm

# --- LOAD THE SPACY MODEL ---
# This is a crucial optimization: load the model only ONCE.
# We disable components we don't need (ner, parser) to speed up processing.
# We only need the 'senter' (sentence recognizer) component.
try:
    NLP = spacy.load("zh_core_web_trf", disable=["ner", "parser"])
    NLP.add_pipe('sentencizer')
    NLP.max_length = 2000000 # Increase max length for long documents
    print("spaCy model 'zh_core_web_trf' loaded successfully.")
except OSError:
    print("spaCy model not found. Please run: python -m spacy download en_core_web_trf")
    exit()

def parse_and_reconstruct(text: str) -> str:
    """
    Uses spaCy to perform accurate sentence boundary detection and reconstructs
    the document with clean paragraph and sentence structure.
    
    Args:
        text: The text cleaned by the Stage 1 script.
        
    Returns:
        A string with validated sentences and paragraph breaks.
    """
    
    # Text is split into paragraphs based on the double newlines from Stage 1.
    paragraphs = text.split('\n\n')
    reconstructed_paragraphs = []

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        # Process the paragraph with spaCy
        doc = NLP(para)
        
        reconstructed_sentences = []
        for sent in doc.sents:
            # For each sentence spaCy finds, we clean it up:
            # 1. .strip() removes leading/trailing whitespace.
            # 2. .replace('\n', ' ') handles any lingering single newlines within a sentence.
            clean_sentence = sent.text.strip().replace('\n', ' ')
            reconstructed_sentences.append(clean_sentence)
        
        # Join the validated sentences back together to form a clean paragraph.
        reconstructed_paragraphs.append(" ".join(reconstructed_sentences))
        
    # Join the clean paragraphs with double newlines to restore the document structure.
    return "\n\n".join(reconstructed_paragraphs)


def process_directory(input_dir: str, output_dir: str):
    """
    Processes all .txt files from the Stage 1 output directory.
    """
    if not os.path.isdir(input_dir):
        print(f"Error: Input directory not found at {input_dir}")
        return

    os.makedirs(output_dir, exist_ok=True)
    
    filenames = sorted([f for f in os.listdir(input_dir) if f.endswith(".txt")])
    
    if not filenames:
        print(f"No .txt files found in {input_dir}")
        return

    print(f"Found {len(filenames)} files from Stage 1. Starting Stage 2 parsing...")
    
    for filename in tqdm(filenames, desc="Parsing files"):
        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, filename)
        
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                stage1_text = f.read()
            
            stage2_text = parse_and_reconstruct(stage1_text)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(stage2_text)
        except Exception as e:
            print(f"\nCould not process {filename}. Error: {e}")

    print(f"\nStage 2 parsing complete. Structurally sound files are in {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Stage 2: A spaCy-based parser for sentence boundary detection and document reconstruction.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "input_dir", 
        help="Directory containing the cleaned .txt files from Stage 1."
    )
    parser.add_argument(
        "output_dir", 
        help="Directory where the Stage 2 parsed .txt files will be saved."
    )
    args = parser.parse_args()
    
    process_directory(args.input_dir, args.output_dir)
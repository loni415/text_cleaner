import os
import spacy
import argparse
from tqdm import tqdm

# --- LOAD SPACY MODELS ---
# We load both English and Chinese models. We will decide which one to use on a per-file basis.
# We disable components we don't need (ner, parser) to speed up sentence boundary detection.
def load_spacy_model(model_name: str):
    try:
        nlp = spacy.load(model_name, disable=["ner", "parser"])
        nlp.add_pipe('sentencizer')
        nlp.max_length = 2000000  # Increase max length for long documents
        print(f"spaCy model '{model_name}' loaded successfully.")
        return nlp
    except OSError:
        print(f"spaCy model '{model_name}' not found. Please run: python -m spacy download {model_name}")
        return None

# Attempt to load both models at the start
NLP_EN = load_spacy_model("en_core_web_trf")
NLP_ZH = load_spacy_model("zh_core_web_trf")

def contains_chinese(text: str) -> bool:
    """Checks if a string contains any Chinese characters."""
    for char in text:
        if '\u4e00' <= char <= '\u9fff':
            return True
    return False

def parse_and_reconstruct(text: str, nlp_model) -> str:
    """
    Uses a loaded spaCy model to perform accurate sentence boundary detection
    and reconstructs the document with clean paragraph and sentence structure.
    """
    if not nlp_model:
        print("  - WARNING: spaCy model not available. Skipping parsing.")
        return text

    # Text is split into paragraphs based on the double newlines from the previous step.
    paragraphs = text.split('\n\n')
    reconstructed_paragraphs = []

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        doc = nlp_model(para)

        reconstructed_sentences = []
        for sent in doc.sents:
            # Clean up each sentence found by spaCy.
            clean_sentence = sent.text.strip().replace('\n', ' ')
            reconstructed_sentences.append(clean_sentence)

        # Join the validated sentences back together to form a clean paragraph.
        reconstructed_paragraphs.append(" ".join(reconstructed_sentences))

    # Join the clean paragraphs with double newlines to restore document structure.
    return "\n\n".join(reconstructed_paragraphs)


def process_directory(input_dir: str, output_dir: str):
    """
    Processes all .txt files from the rule-cleaning step directory.
    """
    if not os.path.isdir(input_dir):
        print(f"Error: Input directory not found at {input_dir}")
        return

    os.makedirs(output_dir, exist_ok=True)

    filenames = sorted([f for f in os.listdir(input_dir) if f.endswith(".txt")])

    if not filenames:
        print(f"No .txt files found in {input_dir}")
        return

    print(f"--- Found {len(filenames)} files. Starting Step 3: Sentence Parsing... ---")

    for filename in tqdm(filenames, desc="Parsing files"):
        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, filename)

        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                cleaned_text = f.read()

            # Auto-detect language and select the appropriate spaCy model.
            # We check the first 1000 characters for efficiency.
            if contains_chinese(cleaned_text[:1000]):
                tqdm.write(f"  - Detected Chinese text in {filename}. Using 'zh_core_web_trf'.")
                nlp_to_use = NLP_ZH
            else:
                tqdm.write(f"  - Detected English text in {filename}. Using 'en_core_web_trf'.")
                nlp_to_use = NLP_EN

            parsed_text = parse_and_reconstruct(cleaned_text, nlp_to_use)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(parsed_text)
        except Exception as e:
            print(f"\nCould not process {filename}. Error: {e}")

    print(f"\n--- Step 3: Sentence parsing complete. Parsed files are in {output_dir} ---")


if __name__ == "__main__":
    if not NLP_EN and not NLP_ZH:
        print("CRITICAL ERROR: No spaCy models could be loaded. Exiting.")
        exit()

    parser = argparse.ArgumentParser(
        description="Step 3: A spaCy-based parser for sentence boundary detection and document reconstruction.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "input_dir",
        help="Directory containing the rule-cleaned .txt files from Step 2."
    )
    parser.add_argument(
        "output_dir",
        help="Directory where the parsed .txt files will be saved."
    )
    args = parser.parse_args()

    process_directory(args.input_dir, args.output_dir)
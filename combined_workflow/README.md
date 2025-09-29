# Combined Document Cleaning and Refinement Pipeline

This workflow provides a comprehensive, five-step pipeline for cleaning and refining text extracted from various document formats, including PDFs, DOCX, and plain text. It is designed to handle both English and Chinese documents, leveraging a combination of rule-based cleaning, structural parsing, and advanced LLM-based refinement.

The pipeline is broken down into logical, sequential scripts. The output of each step serves as the input for the next, creating a clear and maintainable workflow.

## Pipeline Steps

### 1. `step1_ingest.py`
*   **Purpose:** Ingests source documents and performs initial text extraction.
*   **Technology:** `unstructured` library.
*   **Process:**
    *   Scans a source directory for supported file types (`.pdf`, `.docx`, `.md`, `.txt`).
    *   Uses the `unstructured` library's `hi_res` strategy to extract raw text content, with support for both English and Chinese.
    *   Saves the raw text for each document as a `.txt` file in the output directory.

### 2. `step2_rule_clean.py`
*   **Purpose:** Applies a comprehensive set of rules to remove common noise and artifacts from the extracted text.
*   **Technology:** Regular Expressions (Regex).
*   **Process:**
    *   Removes common academic headers, footers, page numbers, and other conversion artifacts.
    *   Fixes duplicated phrases and removes inline citation markers.
    *   Intelligently rejoins paragraphs that were incorrectly split across multiple lines.
    *   Normalizes whitespace for consistency.

### 3. `step3_sentence_parser.py`
*   **Purpose:** Reconstructs the document with accurate sentence and paragraph boundaries.
*   **Technology:** `spaCy`.
*   **Process:**
    *   Auto-detects whether the document is primarily English or Chinese.
    *   Loads the appropriate `spaCy` model (`en_core_web_trf` or `zh_core_web_trf`).
    *   Uses the model's sentence boundary detection capabilities to correctly segment the text into sentences, fixing issues missed by rule-based methods.

### 4. `step4_llm_prune.py`
*   **Purpose:** Semantically isolates the main narrative body of the document.
*   **Technology:** Ollama LLM (`llama3.1:8b-instruct-fp16`).
*   **Process:**
    *   Uses an LLM to analyze the document and identify the start heading (e.g., "Introduction") and end heading (e.g., "References").
    *   Programmatically "prunes" the document, removing preamble and appendices.
    *   This focuses the final, most intensive refinement step on the core content.

### 5. `step5_llm_refine.py`
*   **Purpose:** Performs a final, detailed polish of the pruned text.
*   **Technology:** Ollama LLM (`llama3.1:8b-instruct-fp16`).
*   **Process:**
    *   Breaks the text into small, overlapping chunks of paragraphs.
    *   Uses an LLM to assign a quality score to each chunk based on its structure and grammar.
    *   For chunks that score below a set threshold, a second LLM prompt is used to "repair" the specific issues.
    *   This "classify-then-repair" approach efficiently refines the text without the high cost of processing the entire document in one go.

## How to Run the Pipeline

The easiest way to run the full pipeline is to use the provided bash script. You will need to have Python, `pip`, and Ollama installed.

1.  **Place your source documents** in a directory (e.g., `source_docs`).
2.  **Run the script:**
    ```bash
    bash run_pipeline.sh /path/to/source_docs
    ```
3.  **Find your results:** The final, cleaned files will be located in the `results/step5_final` directory.
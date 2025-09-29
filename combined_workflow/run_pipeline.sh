#!/bin/bash

# This script runs the complete 5-step document cleaning and refinement pipeline.
# It takes one argument: the path to the directory containing the source documents.

# --- Step 0: Initial Setup and Validation ---

# Ensure a source directory is provided
if [ -z "$1" ]; then
  echo "❌ Error: No source directory provided."
  echo "Usage: $0 /path/to/your/source_documents"
  exit 1
fi

SOURCE_DIR=$1
BASE_DIR="results"

# Check if the source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
  echo "❌ Error: Source directory '$SOURCE_DIR' not found."
  exit 1
fi

echo "--- Starting Document Processing Pipeline ---"
echo "Source documents: $SOURCE_DIR"

# Define directories for each step's output
STEP1_OUTPUT="$BASE_DIR/step1_ingested"
STEP2_OUTPUT="$BASE_DIR/step2_rule_cleaned"
STEP3_OUTPUT="$BASE_DIR/step3_parsed"
STEP4_OUTPUT="$BASE_DIR/step4_pruned"
STEP5_OUTPUT="$BASE_DIR/step5_final"

# Create the directory structure
echo "--- Creating output directories in '$BASE_DIR/'... ---"
mkdir -p $STEP1_OUTPUT
mkdir -p $STEP2_OUTPUT
mkdir -p $STEP3_OUTPUT
mkdir -p $STEP4_OUTPUT
mkdir -p $STEP5_OUTPUT
echo "✅ Directories created."

# --- Step 1: Ingest Documents ---
echo -e "\n--- Running Step 1: Ingesting Documents ---"
python3 step1_ingest.py "$SOURCE_DIR" "$STEP1_OUTPUT"
if [ $? -ne 0 ]; then echo "❌ Step 1 failed."; exit 1; fi
echo "✅ Step 1 complete."

# --- Step 2: Rule-Based Cleaning ---
echo -e "\n--- Running Step 2: Rule-Based Cleaning ---"
python3 step2_rule_clean.py "$STEP1_OUTPUT" "$STEP2_OUTPUT"
if [ $? -ne 0 ]; then echo "❌ Step 2 failed."; exit 1; fi
echo "✅ Step 2 complete."

# --- Step 3: Sentence Parsing ---
echo -e "\n--- Running Step 3: Sentence Parsing with spaCy ---"
python3 step3_sentence_parser.py "$STEP2_OUTPUT" "$STEP3_OUTPUT"
if [ $? -ne 0 ]; then echo "❌ Step 3 failed."; exit 1; fi
echo "✅ Step 3 complete."

# --- Step 4: LLM Pruning ---
echo -e "\n--- Running Step 4: LLM Pruning ---"
python3 step4_llm_prune.py "$STEP3_OUTPUT" "$STEP4_OUTPUT"
if [ $? -ne 0 ]; then echo "❌ Step 4 failed."; exit 1; fi
echo "✅ Step 4 complete."

# --- Step 5: LLM Refinement ---
echo -e "\n--- Running Step 5: LLM Refinement ---"
python3 step5_llm_refine.py "$STEP4_OUTPUT" "$STEP5_OUTPUT"
if [ $? -ne 0 ]; then echo "❌ Step 5 failed."; exit 1; fi
echo "✅ Step 5 complete."

# --- Completion ---
echo -e "\n🎉🎉🎉 Pipeline finished successfully! 🎉🎉🎉"
echo "Final processed files are located in: $STEP5_OUTPUT"
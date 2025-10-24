#!/bin/bash

# Advanced script to convert Chinese keywords to pinyin tokens with annotations
# Usage: ./gen_keyword_advanced.sh [input_file] [output_file]
# If no arguments provided, uses default files

set -e  # Exit on any error

# Default files
INPUT_FILE="${1:-model_data/kws/text/keyword_raw.txt}"
OUTPUT_FILE="${2:-model_data/kws/keywords_final.txt}"

echo "Converting keywords from Chinese to pinyin tokens..."
echo "Input file: $INPUT_FILE"
echo "Output file: $OUTPUT_FILE"

# Convert to tokens
sherpa-onnx-cli text2token \
    --tokens model_data/kws/tokens.txt \
    --tokens-type ppinyin \
    "$INPUT_FILE" \
    "${OUTPUT_FILE}.tmp"

# Add @ annotations for original Chinese text
echo "Adding original text annotations..."
python3 -c "
import sys

# Read the original Chinese text
with open('$INPUT_FILE', 'r', encoding='utf-8') as f:
    original_lines = [line.strip() for line in f.readlines()]

# Read the converted tokens
with open('${OUTPUT_FILE}.tmp', 'r', encoding='utf-8') as f:
    token_lines = [line.strip() for line in f.readlines()]

# Combine them
with open('$OUTPUT_FILE', 'w', encoding='utf-8') as f:
    for orig, tokens in zip(original_lines, token_lines):
        f.write(f'{tokens} @{orig}\n')

print(f'Successfully created {len(original_lines)} keyword entries')
"

# Clean up temporary file
rm "${OUTPUT_FILE}.tmp"

echo "Conversion completed! Output saved to: $OUTPUT_FILE"
echo ""
echo "Generated keywords:"
cat "$OUTPUT_FILE"

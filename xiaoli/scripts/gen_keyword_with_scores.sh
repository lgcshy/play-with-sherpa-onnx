#!/bin/bash

# Script to convert Chinese keywords with boosting scores and thresholds
# Usage: ./gen_keyword_with_scores.sh [input_file] [output_file]

set -e  # Exit on any error

# Default files
INPUT_FILE="${1:-model_data/kws/text/keyword_with_scores.txt}"
OUTPUT_FILE="${2:-model_data/kws/keywords_with_scores_final.txt}"

echo "Converting keywords with scores from Chinese to pinyin tokens..."
echo "Input file: $INPUT_FILE"
echo "Output file: $OUTPUT_FILE"

# Convert to tokens (this preserves the :score #threshold @original format)
sherpa-onnx-cli text2token \
    --tokens model_data/kws/tokens.txt \
    --tokens-type ppinyin \
    "$INPUT_FILE" \
    "$OUTPUT_FILE"

echo "Conversion completed! Output saved to: $OUTPUT_FILE"
echo ""
echo "Generated keywords with scores:"
cat "$OUTPUT_FILE"

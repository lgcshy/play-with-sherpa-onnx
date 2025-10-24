#!/bin/bash

# Script to convert Chinese keywords to pinyin tokens
# Usage: ./gen_keyword.sh
# Note: Input file must include @original_text annotations for ppinyin/fpinyin tokens-type

set -e  # Exit on any error

echo "Converting keywords from Chinese to pinyin tokens..."

sherpa-onnx-cli text2token \
    --tokens model_data/kws/tokens.txt \
    --tokens-type ppinyin \
    model_data/kws/text/keyword_raw.txt \
    model_data/kws/text/keyword_token.txt

echo "Conversion completed! Output saved to: model_data/kws/text/keyword_token.txt"
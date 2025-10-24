#!/bin/bash

# Test script to verify all keyword generation scripts work correctly
# Usage: ./test_keyword_scripts.sh

set -e

echo "🧪 Testing Keyword Generation Scripts"
echo "======================================"
echo ""

# Test 1: Basic conversion
echo "1️⃣ Testing basic keyword conversion..."
./scripts/gen_keyword.sh
if [ -f "model_data/kws/text/keyword_token.txt" ]; then
    echo "✅ Basic conversion successful"
    echo "   Output: $(cat model_data/kws/text/keyword_token.txt | wc -l) lines"
else
    echo "❌ Basic conversion failed"
    exit 1
fi
echo ""

# Test 2: Advanced conversion with annotations
echo "2️⃣ Testing advanced keyword conversion with annotations..."
./scripts/gen_keyword_advanced.sh
if [ -f "model_data/kws/keywords_final.txt" ]; then
    echo "✅ Advanced conversion successful"
    echo "   Output: $(cat model_data/kws/keywords_final.txt | wc -l) lines"
else
    echo "❌ Advanced conversion failed"
    exit 1
fi
echo ""

# Test 3: Conversion with boosting scores
echo "3️⃣ Testing keyword conversion with boosting scores..."
./scripts/gen_keyword_with_scores.sh
if [ -f "model_data/kws/keywords_with_scores_final.txt" ]; then
    echo "✅ Score conversion successful"
    echo "   Output: $(cat model_data/kws/keywords_with_scores_final.txt | wc -l) lines"
else
    echo "❌ Score conversion failed"
    exit 1
fi
echo ""

echo "🎉 All tests passed! Your keyword generation scripts are working correctly."
echo ""
echo "📁 Generated files:"
echo "   - model_data/kws/text/keyword_token.txt (basic tokens)"
echo "   - model_data/kws/keywords_final.txt (with @ annotations)"
echo "   - model_data/kws/keywords_with_scores_final.txt (with scores & thresholds)"
echo ""
echo "🚀 Ready to use in your keyword spotting system!"

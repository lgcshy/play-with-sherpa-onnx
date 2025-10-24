# Keyword Generation Scripts

This directory contains scripts for converting Chinese keywords to pinyin tokens for keyword spotting.

## Scripts Overview

### 1. `gen_keyword.sh` - Basic Conversion
Converts simple Chinese keywords to pinyin tokens.

**Usage:**
```bash
./scripts/gen_keyword.sh
```

**Input:** `model_data/kws/text/keyword_raw.txt`
**Output:** `model_data/kws/text/keyword_token.txt`

### 2. `gen_keyword_advanced.sh` - With Annotations
Converts Chinese keywords to pinyin tokens and adds `@original_text` annotations.

**Usage:**
```bash
./scripts/gen_keyword_advanced.sh [input_file] [output_file]
```

**Default Input:** `model_data/kws/text/keyword_raw.txt`
**Default Output:** `model_data/kws/keywords_final.txt`

### 3. `gen_keyword_with_scores.sh` - With Boosting Scores
Converts Chinese keywords with boosting scores and thresholds to pinyin tokens.

**Usage:**
```bash
./scripts/gen_keyword_with_scores.sh [input_file] [output_file]
```

**Default Input:** `model_data/kws/text/keyword_with_scores.txt`
**Default Output:** `model_data/kws/keywords_with_scores_final.txt`

## Input Format Examples

### Basic Format (`keyword_raw.txt`):
```
你好小立 @你好小立
小立小立 @小立小立
小立同学 @小立同学
```

**⚠️ Important:** When using `ppinyin` or `fpinyin` tokens-type, you MUST include `@original_text` annotations in the input file.

### With Scores (`keyword_with_scores.txt`):
```
你好小立 :2.0 #0.6 @你好小立
小立小立 :2.5 #0.5 @小立小立
小立同学 :2.0 #0.6 @小立同学
```

## Output Format Examples

### Basic Output:
```
n ǐ h ǎo x iǎo l ì
x iǎo l ì x iǎo l ì
x iǎo l ì t óng x ué
```

### With Annotations:
```
n ǐ h ǎo x iǎo l ì @你好小立
x iǎo l ì x iǎo l ì @小立小立
x iǎo l ì t óng x ué @小立同学
```

### With Scores and Annotations:
```
n ǐ h ǎo x iǎo l ì :2.0 #0.6 @你好小立
x iǎo l ì x iǎo l ì :2.5 #0.5 @小立小立
x iǎo l ì t óng x ué :2.0 #0.6 @小立同学
```

## Score Parameters

- **`:2.0`** - Boosting score (higher = more emphasis on this keyword)
- **`#0.6`** - Triggering threshold (lower = easier to trigger, higher = more strict)
- **`@你好小立`** - Original Chinese text for reference

## Dependencies

Make sure you have installed:
```bash
pip install sentencepiece pypinyin
```

## Manual CLI Usage

You can also use the sherpa-onnx-cli directly:

```bash
sherpa-onnx-cli text2token \
    --tokens model_data/kws/tokens.txt \
    --tokens-type ppinyin \
    input.txt output.txt
```

#!/usr/bin/env bash
set -euo pipefail

INPUT_PATH="${1:-data/testing/de}"
PASSWORDS_FILE="${2:-passwords.json}"
OUTPUT_DIR="${3:-normalized_people}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NORMALIZER="$SCRIPT_DIR/normalize_data.py"

mkdir -p "$OUTPUT_DIR"

if [[ -d "$INPUT_PATH" ]]; then
  mapfile -t input_files < <(find "$INPUT_PATH" -maxdepth 1 -type f -name '*.json' | sort)
elif [[ -f "$INPUT_PATH" ]]; then
  input_files=("$INPUT_PATH")
else
  echo "Input path not found: $INPUT_PATH" >&2
  exit 1
fi

count="${#input_files[@]}"
if [[ "$count" -eq 0 ]]; then
  echo "No JSON files found in: $INPUT_PATH" >&2
  exit 1
fi

has_passwords=0
if [[ -f "$PASSWORDS_FILE" ]]; then
  has_passwords=1
fi

for idx in "${!input_files[@]}"; do
  input_file="${input_files[$idx]}"
  id="$(jq -r '.id' "$input_file")"

  if [[ -z "$id" || "$id" == "null" ]]; then
    echo "Skipping file without id: $input_file" >&2
    continue
  fi

  echo "Processing person $((idx + 1))/$count: $id"

  tmp_output="$(mktemp)"
  python3 "$NORMALIZER" "$input_file" "$tmp_output"

  if [[ "$has_passwords" -eq 1 ]]; then
    passwords="$(jq -c --arg id "$id" '.[] | select(.id == $id) | .passwords // []' "$PASSWORDS_FILE")"
    passwords="${passwords:-[]}"
    merged="$(jq --arg passwords "$passwords" '. + {passwords: ($passwords | fromjson)}' "$tmp_output")"
  else
    merged="$(cat "$tmp_output")"
  fi

  output_path="$OUTPUT_DIR/${id}.json"
  printf '%s\n' "$merged" > "$output_path"
  rm "$tmp_output"

  echo "Saved: $output_path"
done

echo "All people normalized and saved in '$OUTPUT_DIR/'"

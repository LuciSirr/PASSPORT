#!/usr/bin/env bash

input_dir="${1:-.}"
output_file="${2:-combined_wordlist.txt}"

> "$output_file"

find "$input_dir" -maxdepth 1 -type f | while read -r file; do
  cat "$file" >> "$output_file"
  echo >> "$output_file"
done

echo "Combined wordlist saved to: $output_file"

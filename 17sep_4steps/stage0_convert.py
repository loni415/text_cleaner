# stage0_convert.py
import json
import os
import argparse
from tqdm import tqdm

def convert_json_to_txt(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    filenames = [f for f in os.listdir(input_dir) if f.endswith(".json")]

    if not filenames:
        print(f"No .json files found in {input_dir}")
        return

    print(f"Found {len(filenames)} files to convert.")
    for filename in tqdm(filenames, desc="Converting JSON to TXT"):
        json_path = os.path.join(input_dir, filename)
        txt_path = os.path.join(output_dir, filename.replace(".json", ".txt"))

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # This assumes the JSON is a list of strings.
            # If structure is different, this is where you'd change the logic.
            if isinstance(data, list):
                text_content = "\n\n".join(str(item) for item in data)
            else:
                # Handle other potential JSON structures if necessary
                text_content = str(data)
            
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(text_content)
        except Exception as e:
            print(f"\nError processing {filename}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert JSON files (list of strings) to TXT.")
    parser.add_argument("input_dir", help="Directory containing raw .json files.")
    parser.add_argument("output_dir", help="Directory to save converted .txt files.")
    args = parser.parse_args()
    convert_json_to_txt(args.input_dir, args.output_dir)
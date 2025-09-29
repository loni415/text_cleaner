import re
from pathlib import Path

def extract_body_by_headings(text: str, start_heading: str, end_heading: str) -> str:
    """
    Extracts the main body of text between a start and an end heading.
    Uses regex to find the headings, which can be simple text.
    """
    print(f"  -> Running: extract_body_by_headings")
    print(f"     - Start: '{start_heading}'")
    print(f"     - End:   '{end_heading}'")
    
    # Escape special regex characters in the user-provided headings
    start_pattern = re.escape(start_heading)
    end_pattern = re.escape(end_heading)
    
    match = re.search(f"{start_pattern}(.*?){end_pattern}", text, re.DOTALL)
    if match:
        print("     - Match found.")
        return match.group(1).strip()
    else:
        print("     - WARNING: No match found for the specified window.")
        return text

def remove_citations(text: str) -> str:
    """
    Removes both simple [1] and complex [2]34-56 style citations.
    Handles both full-width［］and standard [] brackets.
    """
    print(f"  -> Running: remove_citations")
    # This single regex handles: [1], [12], [3]56-57, ［4］, etc.
    pattern = r'\[\d+\](?:\d+-\d+)?|［\d+］(?:\d+-\d+)?'
    cleaned_text = re.sub(pattern, '', text)
    print("     - Citations removed.")
    return cleaned_text

def remove_english_abstract(text: str) -> str:
    """
    Removes the final English abstract section.
    """
    print(f"  -> Running: remove_english_abstract")
    pattern = r'# Insights on the psychological protection work of foreign navies.*'
    cleaned_text = re.sub(pattern, '', text, flags=re.DOTALL)
    print("     - English abstract removed.")
    return cleaned_text

# You can add more pre-vetted cleaning functions here in the future
# def remove_urls(text: str) -> str:
#     ...

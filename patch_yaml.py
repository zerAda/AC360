import os
import glob
import re

topics_dir = r"src\copilot\AC360\topics"
files = glob.glob(os.path.join(topics_dir, "*.mcs.yml"))

for file_path in files:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find userInput: ="..." and replace with userInput: '="..."' if not already quoted
    # We match userInput: =... up to the end of the line
    new_content = []
    modified = False
    for line in content.split("\n"):
        match = re.match(r'^(\s*userInput:\s*)(=".+?:\s*.+")$', line)
        if match:
            # It's an unquoted PowerFx with a colon
            prefix = match.group(1)
            val = match.group(2)
            # Replace inner single quotes with '' if needed, though usually PowerFx uses double quotes
            # Just wrap in single quotes
            new_line = f"{prefix}'{val}'"
            new_content.append(new_line)
            modified = True
        else:
            # Also check if it's just any unquoted PowerFx with a colon
            # e.g., userInput: ="Synthèse ... : ..."
            match_general = re.match(r'^(\s*userInput:\s*)(=".+)$', line)
            if match_general and not line.strip().endswith("'") and ":" in match_general.group(2):
                prefix = match_general.group(1)
                val = match_general.group(2)
                new_line = f"{prefix}'{val}'"
                new_content.append(new_line)
                modified = True
            else:
                new_content.append(line)
    
    if modified:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(new_content))
        print(f"Patched {os.path.basename(file_path)}")

print("Done patching.")

import os
import re

def comment_out_prints(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("print(") and not stripped.startswith("#print("):
            indentation = line[:len(line) - len(stripped)]
            new_lines.append(f"{indentation}#print({line.split('print(',1)[1]}")
        else:
            new_lines.append(line)

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

def scan_and_process(root_folder="."):
    for dirpath, _, filenames in os.walk(root_folder):
        for filename in filenames:
            if filename.endswith(".py"):
                full_path = os.path.join(dirpath, filename)
                comment_out_prints(full_path)

if __name__ == "__main__":
    scan_and_process()
    #print("✅ All print(...) statements have been commented out.")

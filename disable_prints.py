import os

def comment_out_prints(file_path, uncomment=False):
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        stripped = line.lstrip()
        indentation = line[:len(line) - len(stripped)]

        if uncomment:
            # Uncomment lines starting with #print(
            if stripped.startswith("#print("):
                uncommented = stripped[1:]  # remove the '#' only
                new_lines.append(f"{indentation}{uncommented}")
            else:
                new_lines.append(line)
        else:
            # Comment lines starting with print(
            if stripped.startswith("print("):
                new_lines.append(f"{indentation}#{stripped}")
            else:
                new_lines.append(line)

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

def scan_and_process(root_folders, uncomment=False):
    for root_folder in root_folders:
        for dirpath, _, filenames in os.walk(root_folder):
            for filename in filenames:
                if filename.endswith(".py"):
                    full_path = os.path.join(dirpath, filename)
                    comment_out_prints(full_path, uncomment=uncomment)

if __name__ == "__main__":
    folders_to_process = ["commons", "services"]
    uncomment = True  # Set True to uncomment, False to comment prints
    scan_and_process(folders_to_process, uncomment=uncomment)
    #print(f"✅ Prints have been {'uncommented' if uncomment else 'commented'} in specified folders.")

import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from kiwipiepy import Kiwi

def read_file(file_path):
    # Try CP949 first, fallback to UTF-8
    encodings = ['cp949', 'utf-8', 'utf-8-sig']
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                return f.read(), enc
        except UnicodeDecodeError:
            continue
    # If all fail, read with replace error handler
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        return f.read(), 'utf-8 (fallback/replaced)'

def process_file(kiwi, src_path, dest_path):
    try:
        content, used_enc = read_file(src_path)
        if not content.strip():
            # Create empty file if source is empty
            with open(dest_path, 'w', encoding='utf-8') as f:
                pass
            return True, f"Empty file ({used_enc})"
            
        sentences = kiwi.split_into_sents(content, return_tokens=True)
        
        segmented_lines = []
        for sent in sentences:
            formatted_tokens = []
            prev_end = -1
            for token in sent.tokens:
                if prev_end != -1:
                    # Check if there was whitespace between the previous token and the current token
                    if token.start > prev_end:
                        formatted_tokens.append(f" {token.form}/{token.tag}")
                    else:
                        formatted_tokens.append(f"+{token.form}/{token.tag}")
                else:
                    formatted_tokens.append(f"{token.form}/{token.tag}")
                prev_end = token.start + token.len
            
            segmented_lines.append("".join(formatted_tokens))
            
        # Write to destination (UTF-8, no BOM)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(segmented_lines) + "\n")
            
        return True, f"Success ({used_enc})"
    except Exception as e:
        return False, str(e)

def main():
    src_dir = r"C:\AG\style\raw_novel_limin"
    dest_dir = r"C:\AG\style\segmented_novel_limin"
    
    if not os.path.exists(src_dir):
        print(f"Error: Source directory {src_dir} does not exist.")
        sys.exit(1)
        
    # Gather all txt files
    tasks = []
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            if file.endswith('.txt'):
                src_path = os.path.join(root, file)
                
                # Get relative path to maintain folder structure
                rel_path = os.path.relpath(src_path, src_dir)
                
                # Format destination file name: [original_name]_tagged.txt
                dir_name, file_name = os.path.split(rel_path)
                name_part, ext_part = os.path.splitext(file_name)
                dest_file_name = f"{name_part}_tagged{ext_part}"
                dest_path = os.path.join(dest_dir, dir_name, dest_file_name)
                
                tasks.append((src_path, dest_path))
                
    total_files = len(tasks)
    print(f"Found {total_files} files to process.")
    
    start_time = time.time()
    
    # Initialize Kiwi (one instance is fine, kiwipiepy is thread-safe and C++ optimized)
    # We will use multithreading to handle multiple files in parallel
    kiwi = Kiwi()
    
    success_count = 0
    fail_count = 0
    
    # Run with thread pool for handling I/O and distributing tokenization
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as executor:
        future_to_file = {
            executor.submit(process_file, kiwi, src, dest): (src, dest)
            for src, dest in tasks
        }
        
        for idx, future in enumerate(as_completed(future_to_file), 1):
            src, dest = future_to_file[future]
            try:
                success, msg = future.result()
                if success:
                    success_count += 1
                else:
                    fail_count += 1
                    print(f"[{idx}/{total_files}] Failed to process {os.path.basename(src)}: {msg}")
            except Exception as exc:
                fail_count += 1
                print(f"[{idx}/{total_files}] Generated an exception for {os.path.basename(src)}: {exc}")
                
            if idx % 50 == 0 or idx == total_files:
                print(f"Progress: {idx}/{total_files} files processed ({success_count} success, {fail_count} failed).")
                
    elapsed = time.time() - start_time
    print(f"\nProcessing finished in {elapsed:.2f} seconds.")
    print(f"Total processed: {total_files} | Success: {success_count} | Failed: {fail_count}")

if __name__ == "__main__":
    main()

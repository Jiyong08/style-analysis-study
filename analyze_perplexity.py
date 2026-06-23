import os
import sys
import json
import time
import math
import torch
import unicodedata
import numpy as np
from transformers import GPT2LMHeadModel, PreTrainedTokenizerFast

# 공백(Space, Tab, 줄바꿈 등), 모든 문장부호(Punctuation) 및 각종 기호(Symbol)를 완전히 제거하여 순수 음절(글자)만 남깁니다.
# unicodedata 카테고리가 'P'(Punctuation), 'Z'(Separator/공백), 'C'(Control/제어문자), 'S'(Symbol/기호)로 시작하지 않는 문자만 수집합니다.
def clean_text_for_char_count(text):
    return "".join([c for c in text if not (
        unicodedata.category(c).startswith('P') or 
        unicodedata.category(c).startswith('Z') or 
        unicodedata.category(c).startswith('C') or
        unicodedata.category(c).startswith('S')
    )])

def parse_filename(file_name):
    name_only = os.path.splitext(file_name)[0]
    if name_only.endswith('_tagged'):
        name_only = name_only[:-7]
        
    parts = name_only.split('_')
    year = "unknown"
    title = "unknown"
    author = "unknown"
    
    if len(parts) >= 3:
        year = parts[0]
        title = parts[1]
        author = parts[2]
    elif len(parts) == 2:
        title = parts[0]
        author = parts[1]
    elif len(parts) == 1:
        author = author = parts[0]
        
    return year, title, author

def main():
    src_dir = r"C:\AG\style\segmented_novel_limin"
    split_dir = r"C:\AG\style\split_novel"
    dest_dir = r"C:\AG\style\perplexity_analysis_results"
    
    if not os.path.exists(src_dir) or not os.path.exists(split_dir):
        print(f"오류: 입력 대상 폴더가 존재하지 않습니다.")
        sys.exit(1)
        
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"--- 분석 시스템 하드웨어 환경 ---")
    print(f"사용 장치(Device): {device.upper()}")
    if device == "cuda":
        print(f"GPU 명칭: {torch.cuda.get_device_name(0)}")
        print(f"메모리 한도: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
    print(f"----------------------------------\n")
    
    print("KoGPT-2 언어 모델 및 토크나이저 로딩 중 (skt/kogpt2-base-v2)...")
    try:
        tokenizer = PreTrainedTokenizerFast.from_pretrained(
            "skt/kogpt2-base-v2", 
            bos_token='</s>', 
            eos_token='</s>', 
            unk_token='<unk>', 
            pad_token='<pad>', 
            mask_token='<mask>'
        )
        model = GPT2LMHeadModel.from_pretrained("skt/kogpt2-base-v2").to(device)
        model.eval()
        print("모델 및 토크나이저 로딩 완료.\n")
    except Exception as e:
        print(f"모델 로드 실패: {e}")
        sys.exit(1)
        
    tasks = []
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            if file.endswith('.txt'):
                src_path = os.path.join(root, file)
                rel_path = os.path.relpath(src_path, src_dir)
                
                dir_name, file_name = os.path.split(rel_path)
                orig_file_name = file_name.replace('_tagged', '')
                split_file_name = f"split_{orig_file_name}"
                split_path = os.path.join(split_dir, dir_name, split_file_name)
                
                name_part, _ = os.path.splitext(file_name)
                dest_file_name = f"{name_part.replace('_tagged', '')}_perplexity.json"
                dest_path = os.path.join(dest_dir, dir_name, dest_file_name)
                
                tasks.append((src_path, split_path, dest_path, dir_name))
                
    total_files = len(tasks)
    print(f"총 {total_files}개의 소설 파일을 탐색했습니다.")
    
    start_time = time.time()
    success_count = 0
    fail_count = 0
    excluded_display_count = 0
    
    with torch.no_grad():
        for idx, (src, split, dest, author_folder) in enumerate(tasks, 1):
            is_excluded = (author_folder == "단편인저자")
            
            try:
                if not os.path.exists(split):
                    continue
                    
                with open(split, 'r', encoding='utf-8') as f:
                    sentences = [line.strip() for line in f.readlines() if line.strip()]
                    
                sentence_word_lengths = []
                sentence_char_lengths = []
                
                for cleaned in sentences:
                    # 어절 수 계산
                    words_count = len(cleaned.split())
                    sentence_word_lengths.append(words_count)
                    
                    # 1. 문장당 순수 글자 수 계산 (공백 및 문장부호 제외)
                    cleaned_chars = clean_text_for_char_count(cleaned)
                    sentence_char_lengths.append(len(cleaned_chars))
                        
                if not sentences:
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    with open(dest, 'w', encoding='utf-8') as f:
                        json.dump({"error": "No valid sentences"}, f)
                    continue
                    
                # 버스트성 계산 (순수 글자수 갱신값 반영)
                word_mean = np.mean(sentence_word_lengths) if sentence_word_lengths else 1.0
                word_std = np.std(sentence_word_lengths) if sentence_word_lengths else 0.0
                burstiness_words = float(word_std / word_mean) if word_mean > 0 else 0.0
                
                char_mean = np.mean(sentence_char_lengths) if sentence_char_lengths else 1.0
                char_std = np.std(sentence_char_lengths) if sentence_char_lengths else 0.0
                burstiness_chars = float(char_std / char_mean) if char_mean > 0 else 0.0
                
                # GPT-2 Causal LM을 사용한 Perplexity(PPL) 계산
                ppl_list = []
                for sent in sentences:
                    inputs = tokenizer(sent, return_tensors="pt").to(device)
                    input_ids = inputs["input_ids"]
                    if input_ids.shape[1] > 1020 or input_ids.shape[1] <= 1:
                        continue
                        
                    outputs = model(input_ids, labels=input_ids)
                    loss = outputs.loss.item()
                    
                    if not math.isnan(loss) and loss < 20:
                        ppl = math.exp(loss)
                        ppl_list.append(ppl)
                        
                ppl_mean = float(np.mean(ppl_list)) if ppl_list else 0.0
                ppl_median = float(np.median(ppl_list)) if ppl_list else 0.0
                ppl_std = float(np.std(ppl_list)) if ppl_list else 0.0
                
                year, title, author = parse_filename(os.path.basename(src))
                
                result = {
                    "metadata": {
                        "file_name": os.path.basename(src),
                        "author": author,
                        "title": title,
                        "year": year,
                        "is_excluded_from_display": is_excluded
                    },
                    "perplexity_metrics": {
                        "sentence_ppls": ppl_list,
                        "mean_ppl": ppl_mean,
                        "median_ppl": ppl_median,
                        "std_ppl": ppl_std
                    },
                    "burstiness_metrics": {
                        "burstiness_words_cv": burstiness_words,
                        "burstiness_chars_cv": burstiness_chars,
                        "sentence_word_lengths": sentence_word_lengths,
                        "sentence_char_lengths": sentence_char_lengths
                    }
                }
                
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                    
                success_count += 1
                if is_excluded:
                    excluded_display_count += 1
                    
            except Exception as e:
                fail_count += 1
                if not is_excluded:
                    print(f"[{idx}/{total_files}] 분석 실패 ({author_folder}): {e}")
                    
            if idx % 50 == 0 or idx == total_files:
                displayed_success = success_count - excluded_display_count
                print(f"진행 상황: {idx}/{total_files} 완료 (제시 대상 성공: {displayed_success}개, 제외됨: {excluded_display_count}개, 실패: {fail_count}개)")
                
    elapsed = time.time() - start_time
    print(f"\n--- 2단계 현대적 PPL & 버스트성 분석 최종 요약 (순수 음절 필터 갱신) ---")
    print(f"소요 시간: {elapsed:.2f} 초")
    print(f"총 처리 파일 수: {total_files}")
    print(f"성공 파일 수 (제시 대상): {success_count - excluded_display_count}")
    print(f"성공 파일 수 (제외 대상 - 단편인저자): {excluded_display_count}")
    print(f"실패 파일 수: {fail_count}")
    print(f"-----------------------------------------\n")

if __name__ == "__main__":
    main()

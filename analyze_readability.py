import os
import sys
import json
import time
import math
import unicodedata
import numpy as np

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
        author = parts[0]
        
    return year, title, author

def analyze_readability_and_entropy(src_path, split_path, dest_path, is_excluded):
    try:
        # split_novel 폴더의 분절 평서문 텍스트 읽기
        if not os.path.exists(split_path):
            return False, f"Split file not found: {split_path}"
            
        with open(split_path, 'r', encoding='utf-8') as f:
            split_lines = [line.strip() for line in f.readlines() if line.strip()]
            
        sentence_count = len(split_lines)
        total_word_count = 0  # 총 어절 수
        long_word_count = 0   # 순수 음절 기준 4자 이상 긴 어절 수 (LIX 가독성용)
        
        for line in split_lines:
            words = line.split()
            for w in words:
                # 어절을 공백으로 스플릿한 후, 기호/공백을 제거한 순수 글자 수를 잽니다.
                cleaned_w = clean_text_for_char_count(w)
                if cleaned_w:
                    total_word_count += 1
                    # 순수 글자 수가 4자 이상인 단어를 "긴 단어"로 카운트 (BOM/기호 제외)
                    if len(cleaned_w) >= 4:
                        long_word_count += 1
                        
        # 형태소 분절 텍스트 로드 및 형태소 엔트로피 계산
        with open(src_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        morpheme_counts = {}
        total_morpheme_count = 0
        
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
                
            words_tagged = line_str.split(' ')
            for w_tag in words_tagged:
                if not w_tag:
                    continue
                morphemes = w_tag.split('+')
                for morph in morphemes:
                    if '/' not in morph:
                        continue
                    parts = morph.rsplit('/', 1)
                    form, tag = parts[0], parts[1]
                    
                    morph_key = f"{form}/{tag}"
                    morpheme_counts[morph_key] = morpheme_counts.get(morph_key, 0) + 1
                    total_morpheme_count += 1
                    
        if sentence_count == 0 or total_word_count == 0 or total_morpheme_count == 0:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with open(dest_path, 'w', encoding='utf-8') as f:
                json.dump({"error": "Empty file or no words found"}, f)
            return True, "No content"
            
        # (1) 정보 엔트로피 (Shannon Entropy) 계산
        entropy = 0.0
        for count in morpheme_counts.values():
            prob = count / total_morpheme_count
            entropy -= prob * math.log2(prob)
            
        # (2) LIX 가독성 (Readability Index) 계산 (순수 글자수 정제값 반영)
        average_sentence_length = total_word_count / sentence_count
        long_word_ratio = (long_word_count * 100) / total_word_count
        lix_score = average_sentence_length + long_word_ratio
        
        # 메타데이터 파싱
        year, title, author = parse_filename(os.path.basename(src_path))
        
        # 결과 구조화
        result = {
            "metadata": {
                "file_name": os.path.basename(src_path),
                "author": author,
                "title": title,
                "year": year,
                "is_excluded_from_display": is_excluded
            },
            "entropy_metrics": {
                "total_morphemes": total_morpheme_count,
                "unique_morphemes": len(morpheme_counts),
                "shannon_entropy": float(entropy)
            },
            "readability_metrics": {
                "total_word_count": total_word_count,
                "long_word_count": long_word_count,
                "average_sentence_length_words": float(average_sentence_length),
                "long_word_ratio_pct": float(long_word_ratio),
                "lix_readability_score": float(lix_score)
            }
        }
        
        # 결과 저장
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
            
        return True, "Success"
    except Exception as e:
        return False, str(e)

def main():
    src_dir = r"C:\AG\style\segmented_novel_limin"
    split_dir = r"C:\AG\style\split_novel"
    dest_dir = r"C:\AG\style\readability_analysis_results"
    
    if not os.path.exists(src_dir) or not os.path.exists(split_dir):
        print(f"오류: 입력 폴더 중 하나가 존재하지 않습니다.")
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
                
                dest_file_name = f"{orig_file_name.replace('.txt', '')}_readability.json"
                dest_path = os.path.join(dest_dir, dir_name, dest_file_name)
                
                tasks.append((src_path, split_path, dest_path, dir_name))
                
    total_files = len(tasks)
    print(f"총 {total_files}개의 소설 파일을 탐색했습니다.")
    
    start_time = time.time()
    success_count = 0
    fail_count = 0
    excluded_display_count = 0
    
    for idx, (src, split, dest, author_folder) in enumerate(tasks, 1):
        is_excluded = (author_folder == "단편인저자")
        
        success, msg = analyze_readability_and_entropy(src, split, dest, is_excluded)
        if success:
            success_count += 1
            if is_excluded:
                excluded_display_count += 1
        else:
            fail_count += 1
            if not is_excluded:
                print(f"[{idx}/{total_files}] 분석 실패 ({author_folder}): {msg}")
                
        if idx % 50 == 0 or idx == total_files:
            displayed_success = success_count - excluded_display_count
            print(f"진행 상황: {idx}/{total_files} 완료 (제시 대상 성공: {displayed_success}개, 제외됨: {excluded_display_count}개, 실패: {fail_count}개)")
            
    elapsed = time.time() - start_time
    print(f"\n--- 4단계 현대적 정보 엔트로피 및 가독성 분석 최종 요약 (순수 음절 필터 갱신) ---")
    print(f"소요 시간: {elapsed:.2f} 초")
    print(f"총 처리 파일 수: {total_files}")
    print(f"성공 파일 수 (제시 대상): {success_count - excluded_display_count}")
    print(f"성공 파일 수 (제외 대상 - 단편인저자): {excluded_display_count}")
    print(f"실패 파일 수: {fail_count}")
    print(f"-----------------------------------------\n")

if __name__ == "__main__":
    main()

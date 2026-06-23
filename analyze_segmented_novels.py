import os
import sys
import json
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed

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

def classify_vx(morph_form, prev_tag):
    if prev_tag == 'VV':
        return 'VX_verb'
    elif prev_tag == 'VA':
        return 'VX_adj'
        
    adj_vx_list = ['싶다', '하다', '않다', '못하다', '그렇다', '듯하다', '법하다', '성싶다', '척하다', '체하다', '직하다']
    if morph_form in adj_vx_list:
        return 'VX_adj'
    return 'VX_verb'

# 문장 종결 방식 분류 함수 정의
# 명사형: 문장부호를 제외한 문장의 마지막 성분(형태소)이 NP, NNP, NNG, NNB, ETN
# 계사형: 문장부호를 제외한 문장의 마지막 어절에 VCP가 포함됨
# 동사형: 문장부호를 제외한 문장의 마지막 어절에 VV, VA, VX, VV-I, VV-R, VA-I, VA-R이 포함됨
def determine_sentence_ending_type(words_tagged):
    clean_words_morphemes = [] # 기호를 제외한 어절별 형태소 리스트
    all_clean_morphemes = []   # 기호를 제외한 전체 형태소 리스트
    
    for w_tag in words_tagged:
        if not w_tag:
            continue
        morphemes = w_tag.split('+')
        word_morphemes = []
        for morph in morphemes:
            if '/' not in morph:
                continue
            parts = morph.rsplit('/', 1)
            form, tag = parts[0], parts[1]
            # 기호 태그(S로 시작)는 분석 판단 대상에서 완전히 제외
            if not tag.startswith('S'):
                word_morphemes.append((form, tag))
                all_clean_morphemes.append((form, tag))
        if word_morphemes:
            clean_words_morphemes.append(word_morphemes)
            
    if not all_clean_morphemes:
        return "기타"
        
    # 1. 명사형 검사 (마지막 성분의 형태소 태그)
    last_morph = all_clean_morphemes[-1]
    last_tag = last_morph[1].upper()
    noun_tags = {'NP', 'NNP', 'NNG', 'NNB', 'ETN'}
    if last_tag in noun_tags:
        return "명사형"
        
    # 마지막 실질 어절의 태그 목록 추출
    last_word_tags = [m[1].upper() for m in clean_words_morphemes[-1]]
    
    # 2. 계사형 검사 (마지막 어절에 VCP 포함)
    if 'VCP' in last_word_tags:
        return "계사형"
        
    # 3. 동사형 검사 (마지막 어절에 VV, VA, VX, VV-I, VV-R, VA-I, VA-R 포함)
    verb_tags = {'VV', 'VA', 'VX', 'VV-I', 'VV-R', 'VA-I', 'VA-R'}
    if any(t in verb_tags for t in last_word_tags):
        return "동사형"
        
    return "기타"

def analyze_single_file(src_path, split_path, dest_path):
    try:
        # split_novel 폴더의 분절 텍스트 읽기
        if not os.path.exists(split_path):
            return False, f"Split file not found: {split_path}"
            
        with open(split_path, 'r', encoding='utf-8') as f:
            split_lines = [line.strip() for line in f.readlines() if line.strip()]
            
        sentence_count = len(split_lines)
        sentence_char_lengths = []
        sentence_word_lengths = []
        word_char_lengths = []
        
        for line in split_lines:
            # 1. 문장당 순수 글자 수 (공백, 문장부호 제외)
            cleaned_line = clean_text_for_char_count(line)
            sentence_char_lengths.append(len(cleaned_line))
            
            # 2. 문장당 어절 수 (띄어쓰기 기준 단어 수는 띄어쓰기를 기준으로 분리하되, 어절 자체는 원형 유지)
            words = line.split()
            sentence_word_lengths.append(len(words))
            
            # 3. 각 개별 어절(단어)당 순수 글자 수 (공백, 문장부호 제외)
            for w in words:
                cleaned_w = clean_text_for_char_count(w)
                if cleaned_w: # 문장부호로만 이루어진 어절(예: "...")은 음절 수가 0이 되므로 제외 처리
                    word_char_lengths.append(len(cleaned_w))
                
        # 형태소 태깅 파일 읽기 및 집계
        with open(src_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        file_name = os.path.basename(src_path)
        year, title, author = parse_filename(file_name)
        
        morpheme_frequencies = {}
        etm_detail_freq = {}
        etn_detail_freq = {}
        ending_morphemes = {}
        punctuations = {}
        
        pos_class_frequencies = {
            "nouns_freq": 0,
            "verbs_freq": 0,
            "adjectives_freq": 0,
            "modifiers_freq": 0,
            "particles_freq": 0,
            "endings_freq": 0,
            "nng_freq": 0,
            "nnb_freq": 0,
            "vv_freq": 0,
            "vx_verb_freq": 0,
            "va_freq": 0,
            "vx_adj_freq": 0,
            "etm_freq": 0,
            "etn_freq": 0
        }
        
        noun_tokens = 0
        noun_types = set()
        verb_adj_tokens = 0
        verb_adj_types = set()
        
        total_morpheme_count = 0
        unique_morphemes = set()
        
        sentence_morpheme_lengths = []
        
        # 문장 종결 방식 빈도 초기화
        sentence_ending_counts = {
            "noun_style_count": 0,
            "copula_style_count": 0,
            "verb_style_count": 0,
            "other_style_count": 0
        }
        
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
                
            words_tagged = line_str.split(' ')
            
            # 문장 종결 방식 판별 및 빈도 누적
            ending_type = determine_sentence_ending_type(words_tagged)
            if ending_type == "명사형":
                sentence_ending_counts["noun_style_count"] += 1
            elif ending_type == "계사형":
                sentence_ending_counts["copula_style_count"] += 1
            elif ending_type == "동사형":
                sentence_ending_counts["verb_style_count"] += 1
            else:
                sentence_ending_counts["other_style_count"] += 1
                
            morpheme_in_sentence = 0
            prev_tag = None
            
            for w_tag in words_tagged:
                if not w_tag:
                    continue
                morphemes = w_tag.split('+')
                for morph in morphemes:
                    if '/' not in morph:
                        continue
                    parts = morph.rsplit('/', 1)
                    form, tag = parts[0], parts[1]
                    morpheme_in_sentence += 1
                    total_morpheme_count += 1
                    
                    morph_key = f"{form}/{tag}"
                    unique_morphemes.add(morph_key)
                    morpheme_frequencies[morph_key] = morpheme_frequencies.get(morph_key, 0) + 1
                    
                    if tag == 'ETM':
                        etm_detail_freq[morph_key] = etm_detail_freq.get(morph_key, 0) + 1
                        pos_class_frequencies["etm_freq"] += 1
                    elif tag == 'ETN':
                        etn_detail_freq[morph_key] = etn_detail_freq.get(morph_key, 0) + 1
                        pos_class_frequencies["etn_freq"] += 1
                        
                    if tag == 'EF':
                        ending_morphemes[morph_key] = ending_morphemes.get(morph_key, 0) + 1
                        
                    if tag.startswith('S'):
                        punctuations[morph_key] = punctuations.get(morph_key, 0) + 1
                        
                    if tag in ['NNG', 'NNP', 'NNB', 'NP', 'NR']:
                        pos_class_frequencies["nouns_freq"] += 1
                        noun_tokens += 1
                        noun_types.add(morph_key)
                        if tag == 'NNG':
                            pos_class_frequencies["nng_freq"] += 1
                        elif tag == 'NNB':
                            pos_class_frequencies["nnb_freq"] += 1
                            
                    elif tag == 'VV':
                        pos_class_frequencies["verbs_freq"] += 1
                        pos_class_frequencies["vv_freq"] += 1
                        verb_adj_tokens += 1
                        verb_adj_types.add(morph_key)
                    elif tag == 'VA':
                        pos_class_frequencies["adjectives_freq"] += 1
                        pos_class_frequencies["va_freq"] += 1
                        verb_adj_tokens += 1
                        verb_adj_types.add(morph_key)
                    elif tag == 'VX':
                        vx_class = classify_vx(form, prev_tag)
                        if vx_class == 'VX_verb':
                            pos_class_frequencies["verbs_freq"] += 1
                            pos_class_frequencies["vx_verb_freq"] += 1
                        else:
                            pos_class_frequencies["adjectives_freq"] += 1
                            pos_class_frequencies["vx_adj_freq"] += 1
                        verb_adj_tokens += 1
                        verb_adj_types.add(morph_key)
                        
                    elif tag in ['MM', 'MAG']:
                        pos_class_frequencies["modifiers_freq"] += 1
                        
                    elif tag.startswith('J'):
                        pos_class_frequencies["particles_freq"] += 1
                        
                    if tag.startswith('E'):
                        pos_class_frequencies["endings_freq"] += 1
                        
                    prev_tag = tag
            
            if morpheme_in_sentence > 0:
                sentence_morpheme_lengths.append(morpheme_in_sentence)
                
        # 문장 종결 방식 비율 계산
        total_ending_analyzed = sum(sentence_ending_counts.values())
        sentence_ending_metrics = {
            "noun_style_count": sentence_ending_counts["noun_style_count"],
            "copula_style_count": sentence_ending_counts["copula_style_count"],
            "verb_style_count": sentence_ending_counts["verb_style_count"],
            "other_style_count": sentence_ending_counts["other_style_count"],
            "noun_style_ratio": sentence_ending_counts["noun_style_count"] / total_ending_analyzed if total_ending_analyzed > 0 else 0.0,
            "copula_style_ratio": sentence_ending_counts["copula_style_count"] / total_ending_analyzed if total_ending_analyzed > 0 else 0.0,
            "verb_style_ratio": sentence_ending_counts["verb_style_count"] / total_ending_analyzed if total_ending_analyzed > 0 else 0.0,
            "other_style_ratio": sentence_ending_counts["other_style_count"] / total_ending_analyzed if total_ending_analyzed > 0 else 0.0
        }
        
        ttr = len(unique_morphemes) / total_morpheme_count if total_morpheme_count > 0 else 0
        noun_ttr = len(noun_types) / noun_tokens if noun_tokens > 0 else 0
        verb_ttr = len(verb_adj_types) / verb_adj_tokens if verb_adj_tokens > 0 else 0
        
        analysis_result = {
            "metadata": {
                "file_name": file_name,
                "author": author,
                "title": title,
                "year": year
            },
            "sentence_metrics": {
                "sentence_count": sentence_count,
                "sentence_char_lengths": sentence_char_lengths,
                "sentence_word_lengths": sentence_word_lengths,
                "sentence_morpheme_lengths": sentence_morpheme_lengths,
                "word_char_lengths": word_char_lengths
            },
            "sentence_ending_metrics": sentence_ending_metrics,
            "lexical_metrics": {
                "total_morphemes": total_morpheme_count,
                "unique_morphemes": len(unique_morphemes),
                "ttr": ttr,
                "noun_ttr": noun_ttr,
                "verb_ttr": verb_ttr
            },
            "pos_class_frequencies": pos_class_frequencies,
            "specialized_frequencies": {
                "ending_morphemes": ending_morphemes,
                "punctuations": punctuations,
                "etm_detail_freq": etm_detail_freq,
                "etn_detail_freq": etn_detail_freq
            },
            "morpheme_frequencies": morpheme_frequencies
        }
        
        with open(dest_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, ensure_ascii=False, indent=2)
            
        return True, None
    except Exception as e:
        return False, str(e)

def main():
    src_dir = r"C:\AG\style\segmented_novel_limin"
    split_dir = r"C:\AG\style\split_novel"
    dest_dir = r"C:\AG\style\analysis_results"
    
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
                
                dest_file_name = f"{orig_file_name.replace('.txt', '')}_analysis.json"
                dest_path = os.path.join(dest_dir, dir_name, dest_file_name)
                
                tasks.append((src_path, split_path, dest_path))
                
    total_files = len(tasks)
    print(f"총 {total_files}개의 소설 파일을 분석 중...")
    
    start_time = time.time()
    success_count = 0
    fail_count = 0
    
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as executor:
        future_to_file = {
            executor.submit(analyze_single_file, src, split, dest): (src, dest)
            for src, split, dest in tasks
        }
        
        for idx, future in enumerate(as_completed(future_to_file), 1):
            src, dest = future_to_file[future]
            try:
                success, err = future.result()
                if success:
                    success_count += 1
                else:
                    fail_count += 1
                    print(f"[{idx}/{total_files}] 분석 실패 {os.path.basename(src)}: {err}")
            except Exception as exc:
                fail_count += 1
                print(f"[{idx}/{total_files}] 예외 발생 {os.path.basename(src)}: {exc}")
                
            if idx % 50 == 0 or idx == total_files:
                print(f"진행 상황: {idx}/{total_files} 완료 (성공: {success_count}개, 실패: {fail_count}개)")
                
    elapsed = time.time() - start_time
    print(f"\n분석 작업 완료 (BOM 및 기호 제거 반영).")
    print(f"소요 시간: {elapsed:.2f} 초")
    print(f"성공: {success_count} | 실패: {fail_count}")

if __name__ == "__main__":
    main()

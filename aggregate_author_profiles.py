import os
import sys
import json
import numpy as np

# 1. 통계 요약 연산 함수 정의
# 주어진 숫자 분포 리스트에서 평균, 표준편차, 중앙값, 최솟값, 최댓값을 산출합니다.
def calculate_stats(lengths_list):
    if not lengths_list:
        return {"mean": 0, "std": 0, "median": 0, "min": 0, "max": 0}
    return {
        "mean": float(np.mean(lengths_list)),
        "std": float(np.std(lengths_list)),
        "median": float(np.median(lengths_list)),
        "min": int(np.min(lengths_list)),
        "max": int(np.max(lengths_list))
    }

# 2. 작가별 소설 분석 데이터 종합 함수 정의
def aggregate_single_author(author_name, author_dir, dest_path):
    try:
        json_files = [f for f in os.listdir(author_dir) if f.endswith('.json')]
        if not json_files:
            return False, "No JSON files found"
            
        works = []
        
        # 텍스트 계량 분포 데이터 통합용 리스트
        all_sentence_char_lengths = []
        all_sentence_word_lengths = []
        all_sentence_morpheme_lengths = []
        all_word_char_lengths = [] # 작가의 전체 작품에 등장하는 모든 어절당 음절(글자) 수 리스트 (신규 반영)
        total_sentence_count = 0
        
        # 문장 종결 방식 통합 누적기
        author_ending_counts = {
            "noun_style_count": 0,
            "copula_style_count": 0,
            "verb_style_count": 0,
            "other_style_count": 0
        }
        
        # 어휘 다양도 측정값
        ttr_values = []
        noun_ttr_values = []
        verb_ttr_values = []
        
        # 품사 및 어미 빈도 누적 사전
        total_morpheme_count = 0
        total_pos_frequencies = {}
        total_ending_morphemes = {}
        total_punctuations = {}
        total_etm_detail = {}
        total_etn_detail = {}
        
        # 최빈 형태소(MFW) 누적 사전
        total_morpheme_frequencies = {}
        
        for file_name in json_files:
            file_path = os.path.join(author_dir, file_name)
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            works.append({
                "title": data["metadata"]["title"],
                "year": data["metadata"]["year"],
                "file_name": data["metadata"]["file_name"]
            })
            
            # (1) 문장/어절 단위 계량 지표 확장 집계 (split_novel 기반 갱신 데이터)
            total_sentence_count += data["sentence_metrics"]["sentence_count"]
            all_sentence_char_lengths.extend(data["sentence_metrics"]["sentence_char_lengths"])
            all_sentence_word_lengths.extend(data["sentence_metrics"]["sentence_word_lengths"])
            all_sentence_morpheme_lengths.extend(data["sentence_metrics"]["sentence_morpheme_lengths"])
            
            # 문장 종결 방식 집계 누적
            if "sentence_ending_metrics" in data:
                author_ending_counts["noun_style_count"] += data["sentence_ending_metrics"].get("noun_style_count", 0)
                author_ending_counts["copula_style_count"] += data["sentence_ending_metrics"].get("copula_style_count", 0)
                author_ending_counts["verb_style_count"] += data["sentence_ending_metrics"].get("verb_style_count", 0)
                author_ending_counts["other_style_count"] += data["sentence_ending_metrics"].get("other_style_count", 0)
            
            # 소설 속 모든 개별 어절의 음절 수 리스트 통합 (신규 추가)
            if "word_char_lengths" in data["sentence_metrics"]:
                all_word_char_lengths.extend(data["sentence_metrics"]["word_char_lengths"])
            
            # (2) 어휘 다양도 수집
            ttr_values.append(data["lexical_metrics"]["ttr"])
            noun_ttr_values.append(data["lexical_metrics"]["noun_ttr"])
            verb_ttr_values.append(data["lexical_metrics"]["verb_ttr"])
            
            total_morpheme_count += data["lexical_metrics"]["total_morphemes"]
            
            # (3) 품사 빈도 누적
            for pos_class, freq in data["pos_class_frequencies"].items():
                total_pos_frequencies[pos_class] = total_pos_frequencies.get(pos_class, 0) + freq
                
            # (4) 특화 스타일(종결어미, 문장부호, 전성어미 세부 정보) 누적
            for ending, freq in data["specialized_frequencies"]["ending_morphemes"].items():
                total_ending_morphemes[ending] = total_ending_morphemes.get(ending, 0) + freq
            for punct, freq in data["specialized_frequencies"]["punctuations"].items():
                total_punctuations[punct] = total_punctuations.get(punct, 0) + freq
            for etm, freq in data["specialized_frequencies"]["etm_detail_freq"].items():
                total_etm_detail[etm] = total_etm_detail.get(etm, 0) + freq
            for etn, freq in data["specialized_frequencies"]["etn_detail_freq"].items():
                total_etn_detail[etn] = total_etn_detail.get(etn, 0) + freq
                
            # (5) 전체 형태소 빈도 누적
            for morph, freq in data["morpheme_frequencies"].items():
                total_morpheme_frequencies[morph] = total_morpheme_frequencies.get(morph, 0) + freq
                
        # 작가 레벨 종합 통계 요약 연산 (가중 분포 계산)
        sentence_char_stats = calculate_stats(all_sentence_char_lengths)
        sentence_word_stats = calculate_stats(all_sentence_word_lengths)
        sentence_morpheme_stats = calculate_stats(all_sentence_morpheme_lengths)
        word_char_stats = calculate_stats(all_word_char_lengths) # 작가의 어절(단어)당 음절 수 통계 요약 (신규 추가)
        
        # 작가 레벨 문장 종결 방식 비율 계산
        total_author_sentences = sum(author_ending_counts.values())
        author_ending_metrics = {
            "noun_style_count": author_ending_counts["noun_style_count"],
            "copula_style_count": author_ending_counts["copula_style_count"],
            "verb_style_count": author_ending_counts["verb_style_count"],
            "other_style_count": author_ending_counts["other_style_count"],
            "noun_style_ratio": author_ending_counts["noun_style_count"] / total_author_sentences if total_author_sentences > 0 else 0.0,
            "copula_style_ratio": author_ending_counts["copula_style_count"] / total_author_sentences if total_author_sentences > 0 else 0.0,
            "verb_style_ratio": author_ending_counts["verb_style_count"] / total_author_sentences if total_author_sentences > 0 else 0.0,
            "other_style_ratio": author_ending_counts["other_style_count"] / total_author_sentences if total_author_sentences > 0 else 0.0
        }
        
        # 빈도 기준 내림차순 정렬
        sorted_endings = dict(sorted(total_ending_morphemes.items(), key=lambda item: item[1], reverse=True))
        sorted_punctuations = dict(sorted(total_punctuations.items(), key=lambda item: item[1], reverse=True))
        sorted_etm = dict(sorted(total_etm_detail.items(), key=lambda item: item[1], reverse=True))
        sorted_etn = dict(sorted(total_etn_detail.items(), key=lambda item: item[1], reverse=True))
        sorted_morphemes = dict(sorted(total_morpheme_frequencies.items(), key=lambda item: item[1], reverse=True)[:500])
        
        # 어휘 다양도(TTR) 평균
        avg_ttr = float(np.mean(ttr_values)) if ttr_values else 0
        avg_noun_ttr = float(np.mean(noun_ttr_values)) if noun_ttr_values else 0
        avg_verb_ttr = float(np.mean(verb_ttr_values)) if verb_ttr_values else 0
        
        # 품사군별 점유율 비율 연산
        pos_percentages = {}
        base_morphemes = total_morpheme_count
        if base_morphemes > 0:
            for pos_class, freq in total_pos_frequencies.items():
                pos_percentages[pos_class.replace("_freq", "_ratio")] = float(freq / base_morphemes)
                
        # 종합 작가 프로파일 JSON 구성
        profile = {
            "metadata": {
                "author": author_name,
                "total_works": len(works),
                "works": sorted(works, key=lambda x: x.get("year", ""))
            },
            "sentence_statistics": {
                "total_sentence_count": total_sentence_count,
                "sentence_char_stats": sentence_char_stats,
                "sentence_word_stats": sentence_word_stats,
                "sentence_morpheme_stats": sentence_morpheme_stats,
                "word_char_stats": word_char_stats # 어절당 글자 수 통계 요약 (신규 추가)
            },
            "sentence_ending_statistics": author_ending_metrics,
            "lexical_statistics": {
                "total_morpheme_count": total_morpheme_count,
                "average_ttr": avg_ttr,
                "average_noun_ttr": avg_noun_ttr,
                "average_verb_ttr": avg_verb_ttr
            },
            "pos_frequencies": total_pos_frequencies,
            "pos_ratios": pos_percentages,
            "specialized_statistics": {
                "ending_morphemes": sorted_endings,
                "punctuations": sorted_punctuations,
                "etm_detail_freq": sorted_etm,
                "etn_detail_freq": sorted_etn
            },
            "top_morphemes_mfw": sorted_morphemes
        }
        
        # 파일 쓰기
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, 'w', encoding='utf-8') as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)
            
        return True, f"Success ({len(works)} works integrated)"
    except Exception as e:
        return False, str(e)

def main():
    src_dir = r"C:\AG\style\analysis_results"
    dest_dir = r"C:\AG\style\author_profiles"
    
    if not os.path.exists(src_dir):
        print(f"오류: 원본 폴더 {src_dir}가 존재하지 않습니다.")
        sys.exit(1)
        
    authors = [d for d in os.listdir(src_dir) if os.path.isdir(os.path.join(src_dir, d))]
    print(f"총 {len(authors)}명의 작가 데이터를 취합 중...")
    
    success_count = 0
    fail_count = 0
    
    for author in authors:
        author_dir = os.path.join(src_dir, author)
        dest_path = os.path.join(dest_dir, f"{author}_profile.json")
        
        success, msg = aggregate_single_author(author, author_dir, dest_path)
        if success:
            success_count += 1
        else:
            fail_count += 1
            print(f"취합 실패 ({author}): {msg}")
            
    print(f"\n작가 데이터 취합 완료.")
    print(f"작가 수: {len(authors)} | 성공: {success_count} | 실패: {fail_count}")

if __name__ == "__main__":
    main()

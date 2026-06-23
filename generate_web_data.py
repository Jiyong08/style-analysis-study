import os
import sys
import json
import pandas as pd
import numpy as np

def main():
    basic_csv_path = r"C:\AG\style\authors_comparison.csv"
    modern_csv_path = r"C:\AG\style\modern_authors_comparison.csv"
    basic_profiles_dir = r"C:\AG\style\author_profiles"
    modern_profiles_dir = r"C:\AG\style\modern_author_profiles"
    
    # 작품별 개별 계량 수치를 직접 긁어오기 위한 디렉토리 경로
    analysis_results_dir = r"C:\AG\style\analysis_results"
    readability_results_dir = r"C:\AG\style\readability_analysis_results"
    perplexity_results_dir = r"C:\AG\style\perplexity_analysis_results"
    embeddings_results_dir = r"C:\AG\style\embeddings_analysis_results"
    network_results_dir = r"C:\AG\style\network_analysis_results"
    
    publish_dir = r"C:\AG\style\publish"
    os.makedirs(publish_dir, exist_ok=True)
    
    # 1. 기초 계량 및 분석 데이터 로드 (CSV)
    basic_metrics = []
    if os.path.exists(basic_csv_path):
        df_basic = pd.read_csv(basic_csv_path)
        basic_metrics = df_basic.to_dict(orient='records')
        print(f"기초 계량 데이터 로드 완료 ({len(basic_metrics)}명)")
    else:
        print("경고: 기초 계량 CSV가 존재하지 않습니다.")
        
    # 2. 응용 분석 데이터 로드 (CSV)
    modern_metrics = []
    if os.path.exists(modern_csv_path):
        df_modern = pd.read_csv(modern_csv_path)
        modern_metrics = df_modern.to_dict(orient='records')
        print(f"응용 분석 데이터 로드 완료 ({len(modern_metrics)}명)")
    else:
        print("경고: 응용 분석 CSV가 존재하지 않습니다. (아직 perplexity 계산 진행 중)")

    # 3. 작가별 세부 프로파일 및 작품별 세부 정보 수집
    author_details = {}
    
    # 기초 프로파일 수집
    if os.path.exists(basic_profiles_dir):
        profile_files = [f for f in os.listdir(basic_profiles_dir) if f.endswith('_profile.json')]
        for f in profile_files:
            author_name = f.replace('_profile.json', '')
            if author_name == "단편인저자":
                continue
                
            path = os.path.join(basic_profiles_dir, f)
            with open(path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                
            if author_name not in author_details:
                author_details[author_name] = {"basic": {}, "modern": {}, "works": []}
            author_details[author_name]["basic"] = {
                "metadata": data.get("metadata", {}),
                "sentence_statistics": data.get("sentence_statistics", {}),
                "sentence_ending_statistics": data.get("sentence_ending_statistics", {}),
                "lexical_statistics": data.get("lexical_statistics", {}),
                "pos_ratios": data.get("pos_ratios", {}),
                "specialized_statistics": {
                    "ending_morphemes": data.get("specialized_statistics", {}).get("ending_morphemes", {})
                }
            }
            
            # 각 작가별 폴더의 개별 작품 JSON 파일을 탐색하여 작품별 세부 수치를 수집
            author_results_path = os.path.join(analysis_results_dir, author_name)
            works_list = []
            if os.path.exists(author_results_path):
                work_files = [wf for wf in os.listdir(author_results_path) if wf.endswith('.json')]
                for wf in work_files:
                    work_basic_path = os.path.join(author_results_path, wf)
                    try:
                        with open(work_basic_path, 'r', encoding='utf-8') as wbf:
                            w_data = json.load(wbf)
                        
                        title = w_data["metadata"]["title"]
                        year = w_data["metadata"]["year"]
                        
                        # 기초 지표 요약
                        sent_char_lens = w_data["sentence_metrics"]["sentence_char_lengths"]
                        word_char_lens = w_data["sentence_metrics"]["word_char_lengths"]
                        avg_sent_len = float(np.mean(sent_char_lens)) if sent_char_lens else 0.0
                        avg_word_len = float(np.mean(word_char_lens)) if word_char_lens else 0.0
                        ttr = w_data["lexical_metrics"]["ttr"]
                        
                        # 품사 비율 연산용 총 형태소 수 로드
                        total_morphs = w_data["lexical_metrics"]["total_morphemes"]
                        pos_freq = w_data.get("pos_class_frequencies", {})
                        
                        def get_ratio(key):
                            return pos_freq.get(key, 0) / total_morphs if total_morphs > 0 else 0.0
                        
                        nouns_ratio = get_ratio("nouns_freq")
                        verbs_ratio = get_ratio("verbs_freq")
                        adjectives_ratio = get_ratio("adjectives_freq")
                        particles_ratio = get_ratio("particles_freq")
                        endings_ratio = get_ratio("endings_freq")
                        nng_ratio = get_ratio("nng_freq")
                        nnb_ratio = get_ratio("nnb_freq")
                        vv_ratio = get_ratio("vv_freq")
                        vx_verb_ratio = get_ratio("vx_verb_freq")
                        va_ratio = get_ratio("va_freq")
                        etm_ratio = get_ratio("etm_freq")
                        etn_ratio = get_ratio("etn_freq")
                        
                        # 종결 지표
                        ending_data = w_data.get("sentence_ending_metrics", {})
                        noun_ending = ending_data.get("noun_style_ratio", 0.0)
                        copula_ending = ending_data.get("copula_style_ratio", 0.0)
                        verb_ending = ending_data.get("verb_style_ratio", 0.0)
                        
                        # 응용 지표 (LIX 가독성) 로드
                        lix_score = 0.0
                        work_read_name = wf.replace('_analysis.json', '_readability.json')
                        work_read_path = os.path.join(readability_results_dir, author_name, work_read_name)
                        if os.path.exists(work_read_path):
                            with open(work_read_path, 'r', encoding='utf-8') as wrf:
                                r_data = json.load(wrf)
                                lix_score = r_data.get("readability_metrics", {}).get("lix_readability_score", 0.0)
                                
                        # 응용 지표 (PPL) 로드
                        ppl_score = 0.0
                        work_ppl_name = wf.replace('_analysis.json', '_perplexity.json')
                        work_ppl_path = os.path.join(perplexity_results_dir, author_name, work_ppl_name)
                        if os.path.exists(work_ppl_path):
                            with open(work_ppl_path, 'r', encoding='utf-8') as wpf:
                                p_data = json.load(wpf)
                                ppl_score = p_data.get("perplexity_metrics", {}).get("mean_ppl", 0.0)

                        # 응용 지표 (의미흐름, 개념유사도) 로드
                        semantic_flow_val = 0.0
                        semantic_div_val = 0.0
                        work_embed_name = wf.replace('_analysis.json', '_embeddings.json')
                        work_embed_path = os.path.join(embeddings_results_dir, author_name, work_embed_name)
                        if os.path.exists(work_embed_path):
                            with open(work_embed_path, 'r', encoding='utf-8') as wef:
                                e_data = json.load(wef)
                                semantic_flow_val = e_data.get("semantic_flow", {}).get("mean_flow", 0.0)
                                semantic_div_val = e_data.get("semantic_diversity", {}).get("mean_similarity_to_average", 0.0)

                        # 응용 지표 (네트워크 밀도) 로드
                        network_density_val = 0.0
                        work_net_name = wf.replace('_analysis.json', '_network.json')
                        work_net_path = os.path.join(network_results_dir, author_name, work_net_name)
                        if os.path.exists(work_net_path):
                            with open(work_net_path, 'r', encoding='utf-8') as wnf:
                                n_data = json.load(wnf)
                                network_density_val = n_data.get("network_metrics", {}).get("density", 0.0)
                                
                        works_list.append({
                            "title": title,
                            "year": year,
                            "avg_sent_len": avg_sent_len,
                            "avg_word_len": avg_word_len,
                            "ttr": ttr,
                            "lix": lix_score,
                            "ppl": ppl_score,
                            "noun_ending": noun_ending,
                            "copula_ending": copula_ending,
                            "verb_ending": verb_ending,
                            # 신규 품사 비율 추가
                            "nouns_ratio": nouns_ratio,
                            "verbs_ratio": verbs_ratio,
                            "adjectives_ratio": adjectives_ratio,
                            "particles_ratio": particles_ratio,
                            "endings_ratio": endings_ratio,
                            "nng_ratio": nng_ratio,
                            "nnb_ratio": nnb_ratio,
                            "vv_ratio": vv_ratio,
                            "vx_verb_ratio": vx_verb_ratio,
                            "va_ratio": va_ratio,
                            "etm_ratio": etm_ratio,
                            "etn_ratio": etn_ratio,
                            # 신규 작품 응용 지표 추가
                            "semantic_flow": semantic_flow_val,
                            "semantic_diversity": semantic_div_val,
                            "network_density": network_density_val
                        })
                    except Exception as ex:
                        print(f"작품 분석 파일 로드 에러 ({wf}): {ex}")
            
            author_details[author_name]["works"] = sorted(works_list, key=lambda x: x.get("year", ""))
            
    # 현대적 프로파일 수집
    if os.path.exists(modern_profiles_dir):
        profile_files = [f for f in os.listdir(modern_profiles_dir) if f.endswith('_modern_profile.json')]
        for f in profile_files:
            author_name = f.replace('_modern_profile.json', '')
            if author_name == "단편인저자":
                continue
                
            path = os.path.join(modern_profiles_dir, f)
            with open(path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                
            if author_name not in author_details:
                author_details[author_name] = {"basic": {}, "modern": {}, "works": []}
            author_details[author_name]["modern"] = {
                "의미흐름_유사도": data.get("의미흐름_유사도", 0),
                "개념유사도_평균": data.get("개념유사도_평균", 0),
                "당혹도_PPL": data.get("당혹도_PPL", 0),
                "버스트성_어절": data.get("버스트성_어절", 0),
                "버스트성_글자": data.get("버스트성_글자", 0),
                "네트워크밀도": data.get("네트워크밀도", 0),
                "네트워크군집도": data.get("네트워크군집도", 0),
                "네트워크이행성": data.get("네트워크이행성", 0),
                "정보엔트로피": data.get("정보엔트로피", 0),
                "가독성_LIX": data.get("가독성_LIX", 0)
            }
            
    # 4. publish/data.js 파일로 출력
    js_content = f"""// 문체 분석 웹 공개용 데이터셋 (자동 생성됨)
const BASIC_METRICS = {json.dumps(basic_metrics, ensure_ascii=False, indent=2)};

const MODERN_METRICS = {json.dumps(modern_metrics, ensure_ascii=False, indent=2)};

const AUTHOR_DETAILS = {json.dumps(author_details, ensure_ascii=False, indent=2)};
"""
    
    dest_path = os.path.join(publish_dir, "data.js")
    with open(dest_path, 'w', encoding='utf-8') as file:
        file.write(js_content)
        
    print(f"웹 데이터 파일 저장 완료 (작품 세부품사 비율 결합): {dest_path}")

if __name__ == "__main__":
    main()

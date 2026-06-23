import os
import sys
import json
import time
from itertools import combinations
import networkx as nx

# 1. 소설 파일명 파싱 함수 정의
# 파일명에서 속성 메타데이터(연도, 제목, 작가)를 분리합니다.
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

# 2. 문장에서 실질 의미 명사(NNG, NNP) 추출 함수 정의
# 의존명사(NNB)나 대명사(NP)는 문맥적 핵심 의미를 지니지 않으므로 일반명사(NNG)와 고유명사(NNP)만 추출합니다.
def extract_meaningful_nouns(tagged_line):
    words = tagged_line.strip().split(' ')
    nouns = []
    for word in words:
        if not word:
            continue
        morphemes = word.split('+')
        for morph in morphemes:
            if '/' in morph:
                parts = morph.rsplit('/', 1)
                form, tag = parts[0], parts[1]
                # 일반명사(NNG)와 고유명사(NNP)만 필터링
                if tag in ['NNG', 'NNP'] and len(form) > 1: # 한 글자 명사(예: 것, 수, 등)는 노이즈가 크므로 제외
                    nouns.append(form)
    return nouns

def analyze_single_file_network(src_path, dest_path, is_excluded):
    try:
        with open(src_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # 문장별 명사 수집 및 전체 명사 빈도 집계
        sentences_nouns = []
        noun_global_counts = {}
        
        for line in lines:
            nouns = extract_meaningful_nouns(line)
            if nouns:
                sentences_nouns.append(nouns)
                for n in nouns:
                    noun_global_counts[n] = noun_global_counts.get(n, 0) + 1
                    
        if not sentences_nouns:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with open(dest_path, 'w', encoding='utf-8') as f:
                json.dump({"error": "No meaningful nouns found"}, f)
            return True, "No nouns"
            
        # 연산 효율성과 분석의 선명성을 위해 최빈 명사 상위 50개만 노드로 선정
        # 노드가 수천 개로 확장되면 공기 네트워크 분석이 불가능해집니다.
        top_nouns = [k for k, v in sorted(noun_global_counts.items(), key=lambda x: x[1], reverse=True)[:50]]
        top_nouns_set = set(top_nouns)
        
        # 3. NetworkX 무방향 그래프 정의 및 에지 가중치 집계
        # 같은 문장 안에 상위 50대 명사들이 함께 출현할 경우 이들 간의 동시 출현(Co-occurrence) 빈도를 누적합니다.
        G = nx.Graph()
        G.add_nodes_from(top_nouns)
        
        for nouns in sentences_nouns:
            # 문장 안의 명사 중 상위 50개 노드에 포함되는 대상들만 필터링
            filtered_nouns = list(set([n for n in nouns if n in top_nouns_set]))
            if len(filtered_nouns) >= 2:
                # 조합(Combination)을 생성하여 가능한 모든 무방향 쌍에 가중치를 부여합니다.
                for n1, n2 in combinations(filtered_nouns, 2):
                    if G.has_edge(n1, n2):
                        G[n1][n2]['weight'] += 1
                    else:
                        G.add_edge(n1, n2, weight=1)
                        
        # 4. 네트워크 지표 연산
        # (1) 밀도 (Density): 전체 네트워크가 얼마나 조밀하고 얽혀 있는지 파악 (0~1)
        density = nx.density(G)
        
        # (2) 군집 계수 (Clustering Coefficient): 단어들끼리 얼마나 끼리끼리 뭉쳐다니는지 평균 계수 측정
        avg_clustering = nx.average_clustering(G)
        
        # (3) 이행성 (Transitivity): 네트워크 전반에서 삼각 관계(A-B, B-C가 연결될 때 A-C도 연결되는 구조)가 나타나는 비율
        transitivity = nx.transitivity(G)
        
        # (4) 중심성(Centrality) 연산
        # 연결 중심성: 다른 명사들과 가장 많은 에지를 가진 키워드
        deg_centrality = nx.degree_centrality(G)
        sorted_deg = sorted(deg_centrality.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # 매개 중심성: 단어와 단어를 잇는 '길목(Bridge)' 역할을 가장 많이 수행하는 핵심 키워드 (이야기 전개의 중심 고리)
        # 가중치의 역수(1/weight)를 거리로 사용하여 중요한 흐름을 정확히 산출합니다.
        # 가중치가 클수록 거리가 가까우므로, 1/weight를 거리 피처로 설정합니다.
        for u, v, d in G.edges(data=True):
            d['distance'] = 1.0 / d['weight'] if d['weight'] > 0 else 1.0
            
        bet_centrality = nx.betweenness_centrality(G, weight='distance')
        sorted_bet = sorted(bet_centrality.items(), key=lambda x: x[1], reverse=True)[:5]
        
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
            "network_metrics": {
                "nodes_count": G.number_of_nodes(),
                "edges_count": G.number_of_edges(),
                "density": float(density),
                "average_clustering": float(avg_clustering),
                "transitivity": float(transitivity)
            },
            "centrality_metrics": {
                "top_degree_centrality": [{"word": k, "value": float(v)} for k, v in sorted_deg],
                "top_betweenness_centrality": [{"word": k, "value": float(v)} for k, v in sorted_bet]
            }
        }
        
        # JSON 파일 저장
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
            
        return True, "Success"
    except Exception as e:
        return False, str(e)

def main():
    src_dir = r"C:\AG\style\segmented_novel_limin"
    dest_dir = r"C:\AG\style\network_analysis_results"
    
    if not os.path.exists(src_dir):
        print(f"오류: 원본 폴더 {src_dir}가 존재하지 않습니다.")
        sys.exit(1)
        
    tasks = []
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            if file.endswith('.txt'):
                src_path = os.path.join(root, file)
                rel_path = os.path.relpath(src_path, src_dir)
                
                # 저장 경로 구조 설정
                dir_name, file_name = os.path.split(rel_path)
                name_part, _ = os.path.splitext(file_name)
                dest_file_name = f"{name_part.replace('_tagged', '')}_network.json"
                dest_path = os.path.join(dest_dir, dir_name, dest_file_name)
                
                tasks.append((src_path, dest_path, dir_name))
                
    total_files = len(tasks)
    print(f"총 {total_files}개의 소설 파일을 탐색했습니다.")
    
    start_time = time.time()
    success_count = 0
    fail_count = 0
    excluded_display_count = 0  # 사용자 결과 제시 시 제외할 '단편인저자' 카운트
    
    for idx, (src, dest, author_folder) in enumerate(tasks, 1):
        is_excluded = (author_folder == "단편인저자")
        
        success, msg = analyze_single_file_network(src, dest, is_excluded)
        if success:
            success_count += 1
            if is_excluded:
                excluded_display_count += 1
        else:
            fail_count += 1
            if not is_excluded:
                print(f"[{idx}/{total_files}] 분석 실패 ({author_folder}): {msg}")
                
        # 50개 파일마다 또는 최종 파일 도달 시 진행률 표시 (단편인저자는 출력 통계에서 제외)
        if idx % 50 == 0 or idx == total_files:
            displayed_success = success_count - excluded_display_count
            print(f"진행 상황: {idx}/{total_files} 완료 (제시 대상 성공: {displayed_success}개, 제외됨: {excluded_display_count}개, 실패: {fail_count}개)")
            
    elapsed = time.time() - start_time
    print(f"\n--- 3단계 현대적 텍스트 네트워크 분석 최종 요약 ---")
    print(f"소요 시간: {elapsed:.2f} 초")
    print(f"총 처리 파일 수: {total_files}")
    print(f"성공 파일 수 (제시 대상): {success_count - excluded_display_count}")
    print(f"성공 파일 수 (제외 대상 - 단편인저자): {excluded_display_count}")
    print(f"실패 파일 수: {fail_count}")
    print(f"-----------------------------------------\n")

if __name__ == "__main__":
    main()

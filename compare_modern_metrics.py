import os
import sys
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

# Windows 한글 깨짐 방지 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

def main():
    base_dirs = {
        "embeddings": r"C:\AG\style\embeddings_analysis_results",
        "perplexity": r"C:\AG\style\perplexity_analysis_results",
        "network": r"C:\AG\style\network_analysis_results",
        "readability": r"C:\AG\style\readability_analysis_results"
    }
    
    # 디렉토리 생존 여부 체크
    for name, path in base_dirs.items():
        if not os.path.exists(path):
            print(f"오류: {name} 분석 폴더 ({path})가 존재하지 않습니다.")
            sys.exit(1)
            
    # 전체 작가 목록 수집 (embeddings 기준)
    authors = [d for d in os.listdir(base_dirs["embeddings"]) if os.path.isdir(os.path.join(base_dirs["embeddings"], d))]
    print(f"총 {len(authors)}명의 작가 데이터를 병합합니다.")
    
    author_profiles_list = []
    
    for author in authors:
        # 각 분석 디렉토리 하위의 파일 목록 수집
        author_emb_dir = os.path.join(base_dirs["embeddings"], author)
        json_files = [f for f in os.listdir(author_emb_dir) if f.endswith('.json')]
        
        # 작가 레벨의 지표 수집기
        works_count = 0
        flow_means = []
        diversity_scores = []
        ppl_means = []
        burstiness_words_values = []
        burstiness_chars_values = []
        network_densities = []
        network_clusterings = []
        network_transitivities = []
        shannon_entropies = []
        lix_readability_scores = []
        
        # '단편인저자' 인지 여부 판단
        is_excluded = (author == "단편인저자")
        
        for json_file in json_files:
            file_base = json_file.replace('_embeddings.json', '')
            
            # 각각의 현대적 지표 JSON 파일 경로 설정
            path_emb = os.path.join(base_dirs["embeddings"], author, json_file)
            path_ppl = os.path.join(base_dirs["perplexity"], author, f"{file_base}_perplexity.json")
            path_net = os.path.join(base_dirs["network"], author, f"{file_base}_network.json")
            path_read = os.path.join(base_dirs["readability"], author, f"{file_base}_readability.json")
            
            # 모든 분석 결과 파일이 존재하는지 검증 후 로드
            if not (os.path.exists(path_emb) and os.path.exists(path_ppl) and os.path.exists(path_net) and os.path.exists(path_read)):
                continue
                
            try:
                with open(path_emb, 'r', encoding='utf-8') as f:
                    data_emb = json.load(f)
                with open(path_ppl, 'r', encoding='utf-8') as f:
                    data_ppl = json.load(f)
                with open(path_net, 'r', encoding='utf-8') as f:
                    data_net = json.load(f)
                with open(path_read, 'r', encoding='utf-8') as f:
                    data_read = json.load(f)
                    
                # 에러 데이터 처리
                if "error" in data_emb or "error" in data_ppl or "error" in data_net or "error" in data_read:
                    continue
                    
                works_count += 1
                
                # 지표 수집
                flow_means.append(data_emb["semantic_flow"]["mean_flow"])
                diversity_scores.append(data_emb["semantic_diversity"]["mean_similarity_to_average"])
                ppl_means.append(data_ppl["perplexity_metrics"]["mean_ppl"])
                burstiness_words_values.append(data_ppl["burstiness_metrics"]["burstiness_words_cv"])
                burstiness_chars_values.append(data_ppl["burstiness_metrics"]["burstiness_chars_cv"])
                network_densities.append(data_net["network_metrics"]["density"])
                network_clusterings.append(data_net["network_metrics"]["average_clustering"])
                network_transitivities.append(data_net["network_metrics"]["transitivity"])
                shannon_entropies.append(data_read["entropy_metrics"]["shannon_entropy"])
                lix_readability_scores.append(data_read["readability_metrics"]["lix_readability_score"])
                
            except Exception as e:
                # 개별 파일 읽기 오류 예외 처리
                pass
                
        if works_count == 0:
            continue
            
        # 작가 단위의 평균 통계 산출
        row = {
            "작가": author,
            "작품수": works_count,
            "의미흐름_유사도": float(np.mean(flow_means)),
            "개념유사도_평균": float(np.mean(diversity_scores)), # 낮을수록 다양함
            "당혹도_PPL": float(np.mean(ppl_means)),
            "버스트성_어절": float(np.mean(burstiness_words_values)),
            "버스트성_글자": float(np.mean(burstiness_chars_values)),
            "네트워크밀도": float(np.mean(network_densities)),
            "네트워크군집도": float(np.mean(network_clusterings)),
            "네트워크이행성": float(np.mean(network_transitivities)),
            "정보엔트로피": float(np.mean(shannon_entropies)),
            "가독성_LIX": float(np.mean(lix_readability_scores)),
            "is_excluded": is_excluded
        }
        
        # 작가 프로파일용 개별 JSON 저장 (단편인저자 정보 포함하여 분석 자체는 수행 및 저장)
        dest_profile_dir = r"C:\AG\style\modern_author_profiles"
        os.makedirs(dest_profile_dir, exist_ok=True)
        with open(os.path.join(dest_profile_dir, f"{author}_modern_profile.json"), 'w', encoding='utf-8') as f:
            json.dump(row, f, ensure_ascii=False, indent=2)
            
        author_profiles_list.append(row)
        
    # 전체 데이터프레임 생성
    df_all = pd.DataFrame(author_profiles_list)
    
    # 5. 사용자 결과 제시 시 '단편인저자' 강제 제외 처리
    # 사용자의 핵심 요구사항: "최종 분석 결과를 사용자에게 제시할 때에는 모두 제외하도록 해."
    df_display = df_all[df_all["is_excluded"] == False].copy()
    df_display.drop(columns=["is_excluded"], inplace=True)
    
    # CSV 비교 리포트 저장 (BOM 포함 UTF-8로 엑셀 깨짐 방지)
    csv_path = r"C:\AG\style\modern_authors_comparison.csv"
    df_display.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"제외 대상(단편인저자)이 제거된 비교 CSV를 저장했습니다: {csv_path}")
    
    # 6. 다차원 통계 시각화 (PCA) 진행
    features = [
        "의미흐름_유사도", "개념유사도_평균", "당혹도_PPL", 
        "버스트성_어절", "네트워크밀도", "네트워크군집도", 
        "정보엔트로피", "가독성_LIX"
    ]
    
    X = df_display[features]
    y = df_display["작가"]
    
    # 피처 표준화 (Standard Scaling)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # PCA 실행
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X_scaled)
    
    # PCA 시각화 그리기
    plt.figure(figsize=(14, 10))
    sns.set_style("whitegrid")
    plt.rcParams['font.family'] = 'Malgun Gothic'
    
    plt.scatter(X_pca[:, 0], X_pca[:, 1], c='mediumpurple', edgecolor='w', s=160, alpha=0.85)
    
    # 노드에 작가명 라벨 추가
    for i, author in enumerate(y):
        plt.annotate(
            author, 
            (X_pca[i, 0], X_pca[i, 1]), 
            textcoords="offset points", 
            xytext=(0, 9), 
            ha='center', 
            fontsize=10,
            weight='bold'
        )
        
    explained_variance = pca.explained_variance_ratio_
    plt.title("소설 작가별 현대적 문체 지표 주성분 분석 (PCA)", fontsize=18, pad=20, weight='bold')
    plt.xlabel(f"주성분 1 (설명력: {explained_variance[0]*100:.2f}%)", fontsize=12)
    plt.ylabel(f"주성분 2 (설명력: {explained_variance[1]*100:.2f}%)", fontsize=12)
    
    plt.tight_layout()
    pca_img_path = r"C:\AG\style\modern_author_style_pca.png"
    plt.savefig(pca_img_path, dpi=300)
    plt.close()
    print(f"제외 대상(단편인저자)이 제거된 PCA 차트를 저장했습니다: {pca_img_path}")
    
    # 7. 히트맵 시각화 그리기
    heat_df = df_display.set_index("작가")[features]
    # 가독성 LIX 점수 기준으로 정렬
    heat_df = heat_df.sort_values(by="가독성_LIX", ascending=False)
    
    plt.figure(figsize=(12, 16))
    sns.heatmap(heat_df, annot=True, fmt=".3f", cmap="Purples", linewidths=.5, cbar_kws={'label': '수치'})
    plt.title("작가별 현대적 문체 지표 분포 히트맵", fontsize=16, pad=20, weight='bold')
    plt.tight_layout()
    heatmap_img_path = r"C:\AG\style\modern_author_heatmap.png"
    plt.savefig(heatmap_img_path, dpi=300)
    plt.close()
    print(f"제외 대상(단편인저자)이 제거된 히트맵을 저장했습니다: {heatmap_img_path}")
    
    print("\n현대적 문체 취합 및 시각화 처리가 완료되었습니다!")

if __name__ == "__main__":
    main()

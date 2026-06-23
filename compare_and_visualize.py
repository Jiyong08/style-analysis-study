import os
import sys
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

# Windows 한글 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

def load_author_profiles(profiles_dir):
    data_list = []
    json_files = [f for f in os.listdir(profiles_dir) if f.endswith('_profile.json')]
    
    for file_name in json_files:
        file_path = os.path.join(profiles_dir, file_name)
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        author = data["metadata"]["author"]
        total_works = data["metadata"]["total_works"]
        
        # Sentence metrics
        char_stats = data["sentence_statistics"]["sentence_char_stats"]
        word_stats = data["sentence_statistics"]["sentence_word_stats"]
        
        # Word character metrics (어절당 음절 수 - 신규 갱신 데이터)
        word_char_stats = data["sentence_statistics"].get("word_char_stats", {"mean": 0})
        
        # Sentence ending metrics (문장 종결 방식)
        ending_stats = data.get("sentence_ending_statistics", {
            "noun_style_ratio": 0.0,
            "copula_style_ratio": 0.0,
            "verb_style_ratio": 0.0,
            "other_style_ratio": 0.0
        })
        
        # Lexical statistics
        lex_stats = data["lexical_statistics"]
        
        # POS ratios
        ratios = data["pos_ratios"]
        
        # Top 3 Ending Morphemes
        endings = data["specialized_statistics"]["ending_morphemes"]
        top_endings = list(endings.keys())[:3]
        top_endings_str = ", ".join(top_endings)
        
        is_excluded = (author == "단편인저자")
        
        row = {
            "작가": author,
            "작품수": total_works,
            "평균문장길이_자수": char_stats["mean"],
            "문장길이편차_자수": char_stats["std"],
            "평균문장길이_어절": word_stats["mean"],
            "평균어절길이_글자수": word_char_stats["mean"], # 신규 데이터 반영
            "어휘다양도_TTR": lex_stats["average_ttr"],
            "명사_TTR": lex_stats["average_noun_ttr"],
            "용언_TTR": lex_stats["average_verb_ttr"],
            "명사형종결_비율": ending_stats.get("noun_style_ratio", 0.0),
            "계사형종결_비율": ending_stats.get("copula_style_ratio", 0.0),
            "동사형종결_비율": ending_stats.get("verb_style_ratio", 0.0),
            "기타종결_비율": ending_stats.get("other_style_ratio", 0.0),
            "명사_비율": ratios.get("nouns_ratio", 0),
            "동사_비율": ratios.get("verbs_ratio", 0),
            "형용사_비율": ratios.get("adjectives_ratio", 0),
            "수식언_비율": ratios.get("modifiers_ratio", 0),
            "조사_비율": ratios.get("particles_ratio", 0),
            "어미_비율": ratios.get("endings_ratio", 0),
            "일반명사_비율": ratios.get("nng_ratio", 0),
            "의존명사_비율": ratios.get("nnb_ratio", 0),
            "일반동사_비율": ratios.get("vv_ratio", 0),
            "보조동사_비율": ratios.get("vx_verb_ratio", 0),
            "일반형용사_비율": ratios.get("va_ratio", 0),
            "보조형용사_비율": ratios.get("vx_adj_ratio", 0),
            "관형사형어미_비율": ratios.get("etm_ratio", 0),
            "명사형어미_비율": ratios.get("etn_ratio", 0),
            "주요종결어미": top_endings_str,
            "is_excluded": is_excluded
        }
        data_list.append(row)
        
    return pd.DataFrame(data_list)

def plot_pca(df, output_path):
    # Features for PCA
    features = [
        "평균문장길이_자수", "문장길이편차_자수", "평균어절길이_글자수", "어휘다양도_TTR",
        "명사_비율", "동사_비율", "형용사_비율", "수식언_비율", "조사_비율", "어미_비율",
        "일반명사_비율", "의존명사_비율", "일반동사_비율", "보조동사_비율", "일반형용사_비율",
        "관형사형어미_비율", "명사형어미_비율",
        "명사형종결_비율", "계사형종결_비율", "동사형종결_비율"
    ]
    
    X = df[features]
    y = df["작가"]
    
    # Standardize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Run PCA
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X_scaled)
    
    # Make plot
    plt.figure(figsize=(14, 10))
    sns.set_style("whitegrid")
    plt.rcParams['font.family'] = 'Malgun Gothic'
    
    # Scatter plot
    plt.scatter(X_pca[:, 0], X_pca[:, 1], c='royalblue', edgecolor='w', s=150, alpha=0.8)
    
    # Add annotations
    for i, author in enumerate(y):
        plt.annotate(
            author, 
            (X_pca[i, 0], X_pca[i, 1]), 
            textcoords="offset points", 
            xytext=(0, 8), 
            ha='center', 
            fontsize=10,
            weight='bold'
        )
        
    explained_variance = pca.explained_variance_ratio_
    plt.title("소설 작가별 문체 주성분 분석 (PCA - 수정본)", fontsize=18, pad=20, weight='bold')
    plt.xlabel(f"주성분 1 (설명력: {explained_variance[0]*100:.2f}%)", fontsize=12)
    plt.ylabel(f"주성분 2 (설명력: {explained_variance[1]*100:.2f}%)", fontsize=12)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    
def plot_heatmap(df, output_path):
    # Select key stylistic features
    features = ["명사_비율", "동사_비율", "형용사_비율", "어휘다양도_TTR", "평균어절길이_글자수", "명사형종결_비율", "계사형종결_비율", "동사형종결_비율"]
    
    # Set index to author
    heat_df = df.set_index("작가")[features]
    
    # Sort authors by noun ratio
    heat_df = heat_df.sort_values(by="명사_비율", ascending=False)
    
    plt.figure(figsize=(12, 16))
    plt.rcParams['font.family'] = 'Malgun Gothic'
    
    sns.heatmap(heat_df, annot=True, fmt=".3f", cmap="YlGnBu", linewidths=.5, cbar_kws={'label': '비율 / 수치'})
    plt.title("작가별 주요 문체 지표 분포 히트맵 (수정본)", fontsize=16, pad=20, weight='bold')
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()

def main():
    profiles_dir = r"C:\AG\style\author_profiles"
    if not os.path.exists(profiles_dir):
        print(f"오류: 프로파일 폴더 {profiles_dir}가 존재하지 않습니다.")
        sys.exit(1)
        
    df = load_author_profiles(profiles_dir)
    
    # 단편인저자 최종 결과 표출 시 강제 배제 규칙 적용
    df_display = df[df["is_excluded"] == False].copy()
    df_display.drop(columns=["is_excluded"], inplace=True)
    
    # Save CSV comparison report
    csv_path = r"C:\AG\style\authors_comparison.csv"
    df_display.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"제외 대상(단편인저자)이 제거된 비교 CSV를 저장했습니다: {csv_path}")
    
    # Generate PCA visualization
    pca_img_path = r"C:\AG\style\author_style_pca.png"
    plot_pca(df_display, pca_img_path)
    print(f"제외 대상(단편인저자)이 제거된 PCA scatter plot을 저장했습니다: {pca_img_path}")
    
    # Generate Heatmap visualization
    heatmap_img_path = r"C:\AG\style\author_pos_heatmap.png"
    plot_heatmap(df_display, heatmap_img_path)
    print(f"제외 대상(단편인저자)이 제거된 Heatmap을 저장했습니다: {heatmap_img_path}")
    
    print("\n기본 문체 비교 및 시각화(BOM 제거/수정본) 처리가 완료되었습니다!")

if __name__ == "__main__":
    main()

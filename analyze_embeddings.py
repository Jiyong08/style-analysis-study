import os
import sys
import json
import time
import torch
import numpy as np
from sentence_transformers import SentenceTransformer

# 1. 자연어 문장 복원 함수 정의
# 형태소/태그 형식(예: "하늘/NNG+이/JKS")의 결합 텍스트에서 태그와 기호를 제거하여 자연어 평서문을 복원합니다.
def restore_sentence(tagged_line):
    words = tagged_line.strip().split(' ')
    reconstructed_words = []
    for word in words:
        if not word:
            continue
        morphemes = word.split('+')
        form_parts = []
        for morph in morphemes:
            if '/' in morph:
                parts = morph.rsplit('/', 1)
                form_parts.append(parts[0])
        reconstructed_words.append("".join(form_parts))
    return " ".join(reconstructed_words)

# 2. 문장 간 코사인 유사도 계산 함수 정의
# 고차원 임베딩 벡터 간의 각도를 계산하여 의미적 유사성(0~1 사이값)을 도출합니다.
def cosine_similarity(v1, v2):
    dot_product = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0
    return float(dot_product / (norm_v1 * norm_v2))

# 3. 소설 파일명 파싱 함수 정의
# 파일명 구조([연도]_[제목]_[작가]_tagged.txt)에서 속성 메타데이터를 분리 추출합니다.
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

def main():
    src_dir = r"C:\AG\style\segmented_novel_limin"
    dest_dir = r"C:\AG\style\embeddings_analysis_results"
    
    if not os.path.exists(src_dir):
        print(f"오류: 원본 폴더 {src_dir}가 존재하지 않습니다.")
        sys.exit(1)
        
    # GPU(RTX 3070) 및 장치 설정
    # CUDA 가속이 가능한 경우 GPU를 활용해 연산 속도를 대폭 극대화합니다.
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"--- 분석 시스템 하드웨어 환경 ---")
    print(f"사용 장치(Device): {device.upper()}")
    if device == "cuda":
        print(f"GPU 명칭: {torch.cuda.get_device_name(0)}")
        print(f"메모리 한도: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
    print(f"----------------------------------\n")
    
    # 한국어 NLI 및 STS 태스크에서 성능이 검증된 SBERT 모델 로드
    print("임베딩 모델 로딩 중 (snunlp/KR-SBERT-V40K-klueNLI-augSTS)...")
    model = SentenceTransformer("snunlp/KR-SBERT-V40K-klueNLI-augSTS", device=device)
    print("모델 로딩 완료.\n")
    
    # 대상 파일들 수집
    tasks = []
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            if file.endswith('.txt'):
                src_path = os.path.join(root, file)
                rel_path = os.path.relpath(src_path, src_dir)
                
                # 저장 경로 구조 설정
                dir_name, file_name = os.path.split(rel_path)
                name_part, _ = os.path.splitext(file_name)
                dest_file_name = f"{name_part.replace('_tagged', '')}_embeddings.json"
                dest_path = os.path.join(dest_dir, dir_name, dest_file_name)
                
                tasks.append((src_path, dest_path, dir_name))
                
    total_files = len(tasks)
    print(f"총 {total_files}개의 소설 파일을 탐색했습니다.")
    
    start_time = time.time()
    
    success_count = 0
    fail_count = 0
    excluded_display_count = 0 # 사용자 제시 시 제외할 '단편인저자' 카운트
    
    for idx, (src, dest, author_folder) in enumerate(tasks, 1):
        # '단편인저자'는 분석 연산은 수행하되, 사용자에게 최종 통계를 노출할 때는 필터링 조건으로 활용
        is_excluded = (author_folder == "단편인저자")
        
        try:
            with open(src, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # 형태소 태깅 데이터에서 순수 자연어 평서문 복원
            sentences = []
            for line in lines:
                cleaned = restore_sentence(line)
                if cleaned.strip():
                    sentences.append(cleaned)
                    
            if not sentences:
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, 'w', encoding='utf-8') as f:
                    json.dump({"error": "No valid sentences"}, f)
                continue
                
            # 문장 임베딩 고속 일괄 생성
            # RTX 3070 GPU의 VRAM 메모리에 최적화된 batch_size=128 적용
            embeddings = model.encode(
                sentences, 
                batch_size=128, 
                show_progress_bar=False, 
                convert_to_numpy=True
            )
            
            # (1) 의미론적 흐름 (Semantic Flow) 분석
            # 연속된 인접 문장 간의 코사인 유사도 수집
            semantic_flow = []
            for i in range(len(embeddings) - 1):
                sim = cosine_similarity(embeddings[i], embeddings[i+1])
                semantic_flow.append(sim)
                
            flow_mean = float(np.mean(semantic_flow)) if semantic_flow else 0.0
            flow_std = float(np.std(semantic_flow)) if semantic_flow else 0.0
            
            # (2) 개념적 다양성 (Semantic Diversity) 분석
            # 소설 전체 문장들의 평균 벡터와의 유사도 분포 및 분산 측정
            mean_vector = np.mean(embeddings, axis=0)
            similarities_to_mean = [cosine_similarity(emb, mean_vector) for emb in embeddings]
            
            # 평균 벡터와의 평균 유사도 (값이 낮을수록 소설 내에서 다루는 소재/개념의 폭이 다채롭고 넓음)
            diversity_score = float(np.mean(similarities_to_mean)) if similarities_to_mean else 0.0
            # 임베딩 차원별 값의 평균 분산 크기
            variance_score = float(np.mean(np.var(embeddings, axis=0))) if len(embeddings) > 0 else 0.0
            
            # 메타데이터 파싱
            year, title, author = parse_filename(os.path.basename(src))
            
            # 결과 구조화
            result = {
                "metadata": {
                    "file_name": os.path.basename(src),
                    "author": author,
                    "title": title,
                    "year": year,
                    "is_excluded_from_display": is_excluded
                },
                "semantic_flow": {
                    "raw_similarities": semantic_flow,
                    "mean_flow": flow_mean,
                    "std_flow": flow_std
                },
                "semantic_diversity": {
                    "mean_similarity_to_average": diversity_score,
                    "variance_score": variance_score
                }
            }
            
            # 분석 결과 JSON 파일 저장 (UTF-8)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
                
            success_count += 1
            if is_excluded:
                excluded_display_count += 1
                
        except Exception as e:
            fail_count += 1
            if not is_excluded:
                print(f"[{idx}/{total_files}] 분석 실패 ({author}): {e}")
                
        # 50개 파일마다 또는 최종 파일 도달 시 진행률 표시 (단편인저자는 출력 통계에서 제외)
        if idx % 50 == 0 or idx == total_files:
            displayed_success = success_count - excluded_display_count
            print(f"진행 상황: {idx}/{total_files} 완료 (제시 대상 성공: {displayed_success}개, 제외됨: {excluded_display_count}개, 실패: {fail_count}개)")
            
    elapsed = time.time() - start_time
    print(f"\n--- 1단계 현대적 임베딩 분석 최종 요약 ---")
    print(f"소요 시간: {elapsed:.2f} 초")
    print(f"총 처리 파일 수: {total_files}")
    print(f"성공 파일 수 (제시 대상): {success_count - excluded_display_count}")
    print(f"성공 파일 수 (제외 대상 - 단편인저자): {excluded_display_count}")
    print(f"실패 파일 수: {fail_count}")
    print(f"-----------------------------------------\n")

if __name__ == "__main__":
    main()

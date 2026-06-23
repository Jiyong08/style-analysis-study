import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from kiwipiepy import Kiwi

# 1. 원본 파일 안전 읽기 함수
# cp949 인코딩을 우선 시도하고 실패 시 UTF-8 폴백 처리하여 파일 텍스트를 안정적으로 로드합니다.
def read_file_safe(file_path):
    encodings = ['cp949', 'utf-8', 'utf-8-sig']
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                return f.read(), enc
        except UnicodeDecodeError:
            continue
    # 모든 디코딩 실패 시 손상된 문자 대체 방식으로 로드
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        return f.read(), 'utf-8 (errors-replace)'

# 2. 개별 파일 문장 분절 및 저장 함수
# Kiwi 엔진을 활용해 문맥 기반 문장 분절을 수행하고 결과를 줄바꿈 형식으로 출력 폴더에 저장합니다.
def process_single_file(kiwi, src_path, dest_path):
    try:
        content, used_enc = read_file_safe(src_path)
        if not content.strip():
            # 빈 파일인 경우 빈 결과 파일 생성
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with open(dest_path, 'w', encoding='utf-8') as f:
                pass
            return True, f"Empty file ({used_enc})"
            
        # Kiwi 문장 분절기 호출 (단순 문장 자르기이므로 형태소 토큰 분석은 제외하여 성능 최적화)
        sentences = kiwi.split_into_sents(content, return_tokens=False)
        
        # 각 문장의 순수 텍스트 본문만 추출하여 개행 문자(\n)로 조인
        segmented_sentences = [sent.text.strip() for sent in sentences if sent.text.strip()]
        
        # 출력 경로 폴더 자동 생성 및 저장 (UTF-8, BOM 제외)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(segmented_sentences) + "\n")
            
        return True, f"Success ({used_enc})"
    except Exception as e:
        return False, str(e)

def main():
    src_dir = r"C:\AG\style\raw_novel_limin"
    dest_dir = r"C:\AG\style\split_novel"
    
    if not os.path.exists(src_dir):
        print(f"오류: 원본 폴더 {src_dir}가 존재하지 않습니다.")
        sys.exit(1)
        
    tasks = []
    # raw_novel_limin 폴더를 재귀 탐색하여 원본 소설 파일들을 식별합니다.
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            if file.endswith('.txt'):
                src_path = os.path.join(root, file)
                rel_path = os.path.relpath(src_path, src_dir)
                
                # 원본 폴더 구조(작가 폴더) 체계를 유지하며 저장할 경로 설정
                dir_name, file_name = os.path.split(rel_path)
                
                # 결과 파일명 규칙 적용: 'split_' + '원래파일명'
                dest_file_name = f"split_{file_name}"
                dest_path = os.path.join(dest_dir, dir_name, dest_file_name)
                
                tasks.append((src_path, dest_path))
                
    total_files = len(tasks)
    print(f"총 {total_files}개의 소설 파일을 감지했습니다. 문장 분절을 시작합니다.")
    
    start_time = time.time()
    
    # Kiwi 한국어 형태소 분석기 인스턴스화
    kiwi = Kiwi()
    
    success_count = 0
    fail_count = 0
    
    # 3. CPU 스레드 풀을 활용한 비동기 병렬 분절 연산 수행
    # 32GB RAM 시스템 자원을 충분히 활용해 다중 파일 I/O를 빠르게 분배 처리합니다.
    max_workers = os.cpu_count() or 4
    print(f"병렬 연산 스레드 수: {max_workers}")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(process_single_file, kiwi, src, dest): (src, dest)
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
                    print(f"[{idx}/{total_files}] 분절 실패 ({os.path.basename(src)}): {msg}")
            except Exception as exc:
                fail_count += 1
                print(f"[{idx}/{total_files}] 예외 발생 ({os.path.basename(src)}): {exc}")
                
            if idx % 50 == 0 or idx == total_files:
                print(f"진행 상황: {idx}/{total_files} 완료 (성공: {success_count}개, 실패: {fail_count}개)")
                
    elapsed = time.time() - start_time
    print(f"\n--- 문장 분절 및 저장 결과 요약 ---")
    print(f"소요 시간: {elapsed:.2f} 초")
    print(f"총 처리 파일 수: {total_files} | 성공: {success_count} | 실패: {fail_count}")
    print(f"출력 경로: {dest_dir}")
    print(f"-----------------------------------\n")

if __name__ == "__main__":
    main()

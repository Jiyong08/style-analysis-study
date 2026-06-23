// Premium Stylometry Dashboard Application logic

document.addEventListener("DOMContentLoaded", () => {
    // 1. 상태 변수 및 초기화
    let currentTheme = "dark";
    let activeTab = "dashboard-tab";
    
    // 데이터 정렬 상태 추적
    let basicSortCol = "";
    let basicSortAsc = true;
    let basic2SortCol = "";
    let basic2SortAsc = true;
    let modernSortCol = "";
    let modernSortAsc = true;

    // 작품별 데이터 정렬 상태 추적
    let workBasicSortCol = "";
    let workBasicSortAsc = true;
    let workBasic2SortCol = "";
    let workBasic2SortAsc = true;
    let workModernSortCol = "";
    let workModernSortAsc = true;

    // 전체 작품 평탄화 목록
    let ALL_WORKS = [];
    
    // 작가별 다차원 비교용 상태 변수
    let selectedCompareAuthors = ["김동인", "김유정"]; // 초기 선택값
    let selectedCompareMetrics = ["평균문장길이_자수", "평균어절길이_글자수", "어휘다양도_TTR", "가독성_LIX", "당혹도_PPL"]; // 초기 5대 지표
    
    // Chart 인스턴스 저장소 (재렌더링 시 기존 차트 destory용)
    const charts = {};

    // 2. 가이드 데이터 선언
    const GUIDE_DATA = [
        {
            id: "sent-len",
            title: "평균 문장 길이 (Sentence Length)",
            type: "기초 지표",
            desc: "온점(.), 물음표(?), 느낌표(!) 등을 기준으로 분절한 각 문장들의 순수 음절(공백 및 문장부호 제외) 수 또는 단어 수의 평균값입니다.",
            purpose: "작가가 구사하는 문장의 호흡과 복잡성을 측정합니다.",
            prosCons: "<strong>장점:</strong> 구문의 단순명료함이나 호흡의 속도감을 보여주는 가장 강력한 지표입니다.<br><strong>단점:</strong> 대화체의 비중이나 서술 기법에 따라 구조적 난이도와 무관하게 수치가 낮아질 수 있습니다."
        },
        {
            id: "word-len",
            title: "평균 어절 길이 (Word Length)",
            type: "기초 지표",
            desc: "소설 내에 출현하는 띄어쓰기 단위(어절)에서 기호/공백을 제외한 순수 글자 수의 평균입니다.",
            purpose: "소설의 단어 수준 복잡도 및 한자어/외래어 사용 비중을 유추합니다.",
            prosCons: "<strong>의미:</strong> 평균 어절 자수가 클수록 한자어나 복합어, 현학적 표현의 비중이 큼을 나타냅니다."
        },
        {
            id: "ttr",
            title: "어휘 다양도 (TTR: Type-Token Ratio)",
            type: "기초 지표",
            desc: "전체 사용된 형태소 단어 수(Token) 대비 고유한 형태소 단어의 개수(Type)의 비율입니다.",
            purpose: "작가가 얼마나 풍부하고 다채로운 어휘를 구사하는지 평가합니다.",
            prosCons: "<strong>장점:</strong> 작가의 어휘력과 묘사의 다채로움을 정량화할 수 있습니다.<br><strong>단점:</strong> 텍스트 총길이가 길어질수록 고유 단어 출현율이 자연 감소하므로, 단편과 장편 소설을 1:1로 단순 비교할 때 왜곡이 생깁니다."
        },
        {
            id: "ending-styles",
            title: "문장 종결 방식 (Sentence Endings)",
            type: "기초 지표",
            desc: "문장이 마쳐지는 문법적 형식을 명사형, 계사형, 동사형의 세 범주로 집계한 비율입니다.",
            purpose: "소설의 서사적 속도감과 묘사 및 논조의 성향을 파악합니다.",
            prosCons: "<strong>명사형:</strong> 문장 끝이 체언(명사/대명사/의존명사)이나 명사형 어미(etn)로 끝납니다. 여운과 시적 회화 효과를 줍니다.<br><strong>계사형:</strong> 마지막 어절에 지정사 '이다'(VCP)가 쓰입니다. 설명적이거나 정의를 내리는 차분한 논조를 띱니다.<br><strong>동사형:</strong> 마지막 어절에 일반 용언(동사/형용사/보조용언 등)이 쓰입니다. 동적인 사건 전개나 직접 서사 전달에 강합니다."
        },
        {
            id: "pos-ratios",
            title: "품사별 비율 (POS Ratios)",
            type: "기초 지표",
            desc: "소설 전체 형태소 중 명사, 동사, 형용사, 조사, 어미 등 주요 형태소 대분류가 차지하는 비중입니다.",
            purpose: "작가의 묘사 성향(명사 중심) 대 동작/상태 중심(동사/형용사 중심)의 문체 양상을 규명합니다.",
            prosCons: "<strong>명사 비율:</strong> 정적인 분위기 및 구체적 사물 묘사가 뛰어납니다.<br><strong>동사 비율:</strong> 동적인 사건 전개와 빠른 전개가 특징입니다.<br><strong>형용사 비율:</strong> 주관적 정조, 심상, 감성적 표현의 밀도가 높습니다."
        },
        {
            id: "semantic-flow",
            title: "의미 흐름 유사도 (Semantic Flow)",
            type: "응용 지표",
            desc: "Sentence-BERT 임베딩 모델을 사용해 연속된 인접 문장 벡터 간의 코사인 유사도 평균을 낸 지표입니다.",
            purpose: "이야기나 사건의 의미론적 변화 속도와 일관성을 파악합니다.",
            prosCons: "<strong>의미:</strong> 값이 높을수록 이야기의 전환이 완만하고 문장 간의 연계가 끈끈함을 뜻하며, 낮을수록 장면의 전환이 급격하고 의식의 흐름 기법 등을 다채롭게 사용함을 보여줍니다."
        },
        {
            id: "semantic-diversity",
            title: "개념 유사도 평균 (Semantic Diversity)",
            type: "응용 지표",
            desc: "작품의 모든 문장 임베딩 벡터들과 전체 작품의 평균(Centroid) 벡터 간의 평균 유사도입니다.",
            purpose: "소설 내에서 다루고 있는 주제, 개념, 소재 영역의 다채로움을 평가합니다.",
            prosCons: "<strong>의미:</strong> 값이 낮을수록 평균 중심점에서 멀리 떨어진 다채로운 어휘/소재 문장이 많다는 뜻이므로, 작품의 개념적 스펙트럼이 넓고 다양함을 의미합니다."
        },
        {
            id: "ppl",
            title: "당혹도 (Perplexity / PPL)",
            type: "응용 지표",
            desc: "로컬 한국어 GPT-2 모델을 가동하여, 소설 문장의 단어 결합 방식을 확률적으로 예측하고 모델이 느끼는 당혹스러운 수준을 역산한 지표입니다.",
            purpose: "작가가 문장 구사 시 얼마나 보편적인 문법 관행을 따르는지, 혹은 독창적이고 전형적이지 않은 문장을 쓰는지 측정합니다.",
            prosCons: "<strong>장점:</strong> 작가의 파격적인 문체, 비정형적이고 실험적인 어휘 배치(시적 허용 등)를 탁월하게 잡아냅니다.<br><strong>단점:</strong> 단순 오타나 오번역, 형태소 정제 오류가 있어도 당혹도 점수가 튀어오를 수 있습니다."
        },
        {
            id: "burstiness",
            title: "버스트성 (Burstiness)",
            type: "응용 지표",
            desc: "소설 속 문장 길이들의 편차(표준편차/평균)를 기반으로, 문장 호흡의 불균일함을 계량화한 값입니다.",
            purpose: "작가가 연출하는 문장 길이의 동적인 리듬감과 호흡의 불규칙성을 나타냅니다.",
            prosCons: "<strong>의미:</strong> 값이 낮으면 문장 길이가 획일화되어 평이하고 단조로운 느낌을 줍니다. 값이 높으면 매우 짧은 문장과 엄청나게 긴 문장이 혼재하며 폭발적(Burst)이고 긴장감 넘치는 문장 리듬을 형성합니다."
        },
        {
            id: "text-network",
            title: "네트워크 밀도 (Network Density)",
            type: "응용 지표",
            desc: "작품 내 최빈 명사(NNG/NNP) 상위 50개를 단어 노드로 삼아, 한 문장 내 동시 출현(Co-occurrence) 빈도를 계산하고 이를 연결한 지표 밀도입니다.",
            purpose: "어휘들 간의 긴밀함과 서사 구조의 집중도를 분석합니다.",
            prosCons: "<strong>의미:</strong> 네트워크 밀도가 높고 군집도가 클수록 한정된 대상과 어휘들이 서로 강력하게 결속되어 서사가 매우 촘촘하고 집중력 있게 전개됨을 뜻합니다."
        },
        {
            id: "lix",
            title: "LIX 가독성 지표 (Lix Readability)",
            type: "응용 지표",
            desc: "스웨덴 공학자 Björnsson이 개발한 지식 가독성 수식으로, '평균 문장 길이(단어수) + (4자 이상 긴 단어 비율)'로 산출합니다.",
            purpose: "일반 대독자들이 읽기에 해당 텍스트가 얼마나 읽기 편한지 난이도를 판독합니다.",
            prosCons: "<strong>의미:</strong> 가독성 점수가 20 미만이면 아동용 도서 수준으로 대단히 읽기 쉬우며, 50 이상이면 학술 논문이나 문학적 복잡도가 대단히 높아 고도의 독해력이 필요함을 의미합니다."
        }
    ];

    // 비교 분석에 제공할 메타데이터 설정 (시각화 시 단위 평탄화 처리용 최대값)
    const COMPARE_METRIC_METADATA = [
        { key: "평균문장길이_자수", label: "평균 문장 자수", max: 120 },
        { key: "평균어절길이_글자수", label: "평균 어절 자수", max: 5 },
        { key: "어휘다양도_TTR", label: "어휘 다양도 (TTR)", max: 0.7 },
        { key: "명사_비율", label: "명사 비율", max: 0.5 },
        { key: "동사_비율", label: "동사 비율", max: 0.4 },
        { key: "형용사_비율", label: "형용사 비율", max: 0.2 },
        { key: "조사_비율", label: "조사 비율", max: 0.3 },
        { key: "어미_비율", label: "어미 비율", max: 0.4 },
        { key: "가독성_LIX", label: "가독성 (LIX)", max: 60 },
        { key: "당혹도_PPL", label: "당혹도 (PPL)", max: 2000 },
        { key: "의미흐름_유사도", label: "의미 흐름 유사도", max: 0.9 },
        { key: "네트워크밀도", label: "네트워크 밀도", max: 0.25 }
    ];

    // 3. 돔 엘리먼트 수집
    const navItems = document.querySelectorAll(".nav-item");
    const tabContents = document.querySelectorAll(".tab-content");
    const themeToggleBtn = document.getElementById("theme-toggle-btn");
    const guideList = document.getElementById("guide-list");
    const guideSearchInput = document.getElementById("guide-search-input");
    
    const basicTableBody = document.querySelector("#basic-table tbody");
    const basicHeaders = document.querySelectorAll("#basic-table th");
    
    const basic2TableBody = document.querySelector("#basic-table-2 tbody");
    const basic2Headers = document.querySelectorAll("#basic-table-2 th");
    
    const modernTableBody = document.querySelector("#modern-table tbody");
    const modernHeaders = document.querySelectorAll("#modern-table th");

    const workBasicTableBody = document.querySelector("#work-basic-table tbody");
    const workBasicHeaders = document.querySelectorAll("#work-basic-table th");

    const workBasic2TableBody = document.querySelector("#work-basic-table-2 tbody");
    const workBasic2Headers = document.querySelectorAll("#work-basic-table-2 th");

    const workModernTableBody = document.querySelector("#work-modern-table tbody");
    const workModernHeaders = document.querySelectorAll("#work-modern-table th");
    
    const authorSelect = document.getElementById("author-select");
    const authorDetailsContainer = document.getElementById("author-details-container");
    
    // 모달 엘리먼트
    const modal = document.getElementById("work-detail-modal");
    const modalTitle = document.getElementById("modal-title");
    const modalCloseBtn = document.getElementById("modal-close-btn");
    const modalWorkTableBody = document.querySelector("#modal-work-table tbody");

    // 비교 탭 엘리먼트
    const compareAuthorChipsContainer = document.getElementById("compare-author-chips");
    const compareMetricChipsContainer = document.getElementById("compare-metric-chips");

    // 4. 탭 전환 처리
    navItems.forEach(item => {
        item.addEventListener("click", () => {
            const targetTab = item.getAttribute("data-tab");
            
            navItems.forEach(nav => nav.classList.remove("active"));
            tabContents.forEach(tab => tab.classList.remove("active"));
            
            item.classList.add("active");
            const activeSection = document.getElementById(targetTab);
            activeSection.classList.add("active");
            
            activeTab = targetTab;
            
            handleTabActivation(targetTab);
        });
    });

    // 5. 테마 전환 처리
    themeToggleBtn.addEventListener("click", () => {
        document.body.classList.toggle("light-theme");
        currentTheme = document.body.classList.contains("light-theme") ? "light" : "dark";
        updateAllChartsTheme();
    });

    // 6. 가이드 생성 및 검색 기능
    function renderGuide(filterText = "") {
        guideList.innerHTML = "";
        const lowerFilter = filterText.toLowerCase();
        
        const filtered = GUIDE_DATA.filter(item => 
            item.title.toLowerCase().includes(lowerFilter) || 
            item.type.toLowerCase().includes(lowerFilter) ||
            item.desc.toLowerCase().includes(lowerFilter)
        );
        
        filtered.forEach(item => {
            const guideCard = document.createElement("div");
            guideCard.className = "guide-item";
            guideCard.id = `guide-item-${item.id}`;
            guideCard.innerHTML = `
                <div class="guide-title">
                    <span>${item.title}</span>
                    <span class="guide-meta">${item.type}</span>
                </div>
                <p class="guide-desc">${item.desc}</p>
                <div class="guide-details">
                    <p><strong>측정 목적:</strong> ${item.purpose}</p>
                    ${item.prosCons ? `<p>${item.prosCons}</p>` : ''}
                </div>
            `;
            guideList.appendChild(guideCard);
        });
    }

    guideSearchInput.addEventListener("input", (e) => {
        renderGuide(e.target.value);
    });

    window.highlightGuide = function(guideId) {
        const el = document.getElementById(`guide-item-${guideId}`);
        if (el) {
            el.scrollIntoView({ behavior: "smooth", block: "center" });
            el.style.backgroundColor = "rgba(124, 58, 237, 0.15)";
            el.style.transition = "background-color 0.5s ease";
            setTimeout(() => {
                el.style.backgroundColor = "transparent";
            }, 2000);
        }
    };

    // 7. 모달 창 제어 로직 (작품별 데이터 로드 및 노출)
    function openAuthorWorkModal(authorName, tableId) {
        const authorData = AUTHOR_DETAILS[authorName];
        if (!authorData || !authorData.works) return;

        modalTitle.innerText = `${authorName} 작가 - 작품별 세부 분석 결과`;
        modalWorkTableBody.innerHTML = "";

        const thead = document.querySelector("#modal-work-table thead");

        if (tableId === "basic-table-2" || tableId === "work-basic-table-2") {
            // 기초 계량 및 분석 2인 경우: 품사 및 어미 세부 비율 지표
            thead.innerHTML = `
                <tr>
                    <th>작품명</th>
                    <th>연도</th>
                    <th>명사 비율</th>
                    <th>동사 비율</th>
                    <th>형용사 비율</th>
                    <th>조사 비율</th>
                    <th>어미 비율</th>
                    <th>일반명사</th>
                    <th>의존명사</th>
                    <th>일반동사</th>
                    <th>보조동사</th>
                    <th>일반형용사</th>
                    <th>관형사형어미</th>
                    <th>명사형어미</th>
                </tr>
            `;

            authorData.works.forEach(work => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td><strong>${work.title}</strong></td>
                    <td>${work.year || '미상'}</td>
                    <td>${((work.nouns_ratio || 0) * 100).toFixed(1)}%</td>
                    <td>${((work.verbs_ratio || 0) * 100).toFixed(1)}%</td>
                    <td>${((work.adjectives_ratio || 0) * 100).toFixed(1)}%</td>
                    <td>${((work.particles_ratio || 0) * 100).toFixed(1)}%</td>
                    <td>${((work.endings_ratio || 0) * 100).toFixed(1)}%</td>
                    <td>${((work.nng_ratio || 0) * 100).toFixed(1)}%</td>
                    <td>${((work.nnb_ratio || 0) * 100).toFixed(1)}%</td>
                    <td>${((work.vv_ratio || 0) * 100).toFixed(1)}%</td>
                    <td>${((work.vx_verb_ratio || 0) * 100).toFixed(1)}%</td>
                    <td>${((work.va_ratio || 0) * 100).toFixed(1)}%</td>
                    <td>${((work.etm_ratio || 0) * 100).toFixed(1)}%</td>
                    <td>${((work.etn_ratio || 0) * 100).toFixed(1)}%</td>
                `;
                modalWorkTableBody.appendChild(tr);
            });
        } else {
            // 그 외 (기초 1, 응용 분석)인 경우: 기존 물리 지표
            thead.innerHTML = `
                <tr>
                    <th>작품명</th>
                    <th>연도</th>
                    <th>평균 문장 길이</th>
                    <th>평균 어절 길이</th>
                    <th>어휘 다양도 (TTR)</th>
                    <th>가독성 (LIX)</th>
                    <th>당혹도 (PPL)</th>
                    <th>명사형 종결</th>
                    <th>계사형 종결</th>
                    <th>동사형 종결</th>
                </tr>
            `;

            authorData.works.forEach(work => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td><strong>${work.title}</strong></td>
                    <td>${work.year || '미상'}</td>
                    <td>${work.avg_sent_len.toFixed(1)}자</td>
                    <td>${work.avg_word_len.toFixed(2)}자</td>
                    <td>${work.ttr.toFixed(3)}</td>
                    <td>${work.lix.toFixed(1)}</td>
                    <td>${work.ppl > 0 ? work.ppl.toFixed(1) : '-'}</td>
                    <td>${(work.noun_ending * 100).toFixed(1)}%</td>
                    <td>${(work.copula_ending * 100).toFixed(1)}%</td>
                    <td>${(work.verb_ending * 100).toFixed(1)}%</td>
                `;
                modalWorkTableBody.appendChild(tr);
            });
        }

        modal.classList.add("active");
    }

    modalCloseBtn.addEventListener("click", () => {
        modal.classList.remove("active");
    });

    window.addEventListener("click", (e) => {
        if (e.target === modal) {
            modal.classList.remove("active");
        }
    });

    // 테이블 내 클릭 이벤트 수집기
    document.addEventListener("click", (e) => {
        if (e.target && e.target.classList.contains("clickable-author")) {
            const author = e.target.getAttribute("data-author");
            if (author) {
                const table = e.target.closest("table");
                const tableId = table ? table.id : "";
                openAuthorWorkModal(author, tableId);
            }
        }
    });

    // 8. 테이블 렌더링 및 정렬 처리
    function renderBasicTable(data) {
        basicTableBody.innerHTML = "";
        data.forEach(row => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong class="clickable-author" data-author="${row["작가"]}">${row["작가"]}</strong></td>
                <td>${row["작품수"]}</td>
                <td>${row["평균문장길이_자수"].toFixed(1)}</td>
                <td>${row["평균어절길이_글자수"].toFixed(2)}</td>
                <td>${row["어휘다양도_TTR"].toFixed(3)} <span class="help-icon" onclick="highlightGuide('ttr')">?</span></td>
                <td>${(row["명사형종결_비율"] * 100).toFixed(1)}%</td>
                <td>${(row["계사형종결_비율"] * 100).toFixed(1)}%</td>
                <td>${(row["동사형종결_비율"] * 100).toFixed(1)}% <span class="help-icon" onclick="highlightGuide('ending-styles')">?</span></td>
            `;
            basicTableBody.appendChild(tr);
        });
    }

    function renderBasic2Table(data) {
        basic2TableBody.innerHTML = "";
        data.forEach(row => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong class="clickable-author" data-author="${row["작가"]}">${row["작가"]}</strong></td>
                <td>${(row["명사_비율"] * 100).toFixed(1)}% <span class="help-icon" onclick="highlightGuide('pos-ratios')">?</span></td>
                <td>${(row["동사_비율"] * 100).toFixed(1)}%</td>
                <td>${(row["형용사_비율"] * 100).toFixed(1)}%</td>
                <td>${(row["조사_비율"] * 100).toFixed(1)}%</td>
                <td>${(row["어미_비율"] * 100).toFixed(1)}%</td>
                <td>${(row["일반명사_비율"] * 100).toFixed(1)}%</td>
                <td>${(row["의존명사_비율"] * 100).toFixed(1)}%</td>
                <td>${(row["일반동사_비율"] * 100).toFixed(1)}%</td>
                <td>${(row["보조동사_비율"] * 100).toFixed(1)}%</td>
                <td>${(row["일반형용사_비율"] * 100).toFixed(1)}%</td>
                <td>${(row["관형사형어미_비율"] * 100).toFixed(1)}%</td>
                <td>${(row["명사형어미_비율"] * 100).toFixed(1)}%</td>
            `;
            basic2TableBody.appendChild(tr);
        });
    }

    function renderModernTable(data) {
        if (!data || data.length === 0) {
            modernTableBody.innerHTML = `<tr><td colspan="8" style="text-align:center; color:var(--text-secondary);">응용 분석 데이터 연산이 진행 중입니다. 잠시만 대기해 주세요.</td></tr>`;
            return;
        }
        modernTableBody.innerHTML = "";
        data.forEach(row => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong class="clickable-author" data-author="${row["작가"]}">${row["작가"]}</strong></td>
                <td>${row["의미흐름_유사도"].toFixed(3)} <span class="help-icon" onclick="highlightGuide('semantic-flow')">?</span></td>
                <td>${row["개념유사도_평균"].toFixed(3)} <span class="help-icon" onclick="highlightGuide('semantic-diversity')">?</span></td>
                <td>${row["당혹도_PPL"].toFixed(1)} <span class="help-icon" onclick="highlightGuide('ppl')">?</span></td>
                <td>${row["버스트성_어절"].toFixed(3)}</td>
                <td>${row["버스트성_글자"].toFixed(3)} <span class="help-icon" onclick="highlightGuide('burstiness')">?</span></td>
                <td>${row["네트워크밀도"].toFixed(3)} <span class="help-icon" onclick="highlightGuide('text-network')">?</span></td>
                <td>${row["가독성_LIX"].toFixed(1)} <span class="help-icon" onclick="highlightGuide('lix')">?</span></td>
            `;
            modernTableBody.appendChild(tr);
        });
    }

    function renderWorkBasicTable(data) {
        workBasicTableBody.innerHTML = "";
        data.forEach(row => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>${row["title"]}</strong></td>
                <td><strong class="clickable-author" data-author="${row["작가"]}">${row["작가"]}</strong></td>
                <td>${row["year"] || '미상'}</td>
                <td>${row["avg_sent_len"].toFixed(1)}자</td>
                <td>${row["avg_word_len"].toFixed(2)}자</td>
                <td>${row["ttr"].toFixed(3)}</td>
                <td>${((row["noun_ending"] || 0) * 100).toFixed(1)}%</td>
                <td>${((row["copula_ending"] || 0) * 100).toFixed(1)}%</td>
                <td>${((row["verb_ending"] || 0) * 100).toFixed(1)}%</td>
            `;
            workBasicTableBody.appendChild(tr);
        });
    }

    function renderWorkBasic2Table(data) {
        workBasic2TableBody.innerHTML = "";
        data.forEach(row => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>${row["title"]}</strong></td>
                <td><strong class="clickable-author" data-author="${row["작가"]}">${row["작가"]}</strong></td>
                <td>${((row["nouns_ratio"] || 0) * 100).toFixed(1)}%</td>
                <td>${((row["verbs_ratio"] || 0) * 100).toFixed(1)}%</td>
                <td>${((row["adjectives_ratio"] || 0) * 100).toFixed(1)}%</td>
                <td>${((row["particles_ratio"] || 0) * 100).toFixed(1)}%</td>
                <td>${((row["endings_ratio"] || 0) * 100).toFixed(1)}%</td>
                <td>${((row["nng_ratio"] || 0) * 100).toFixed(1)}%</td>
                <td>${((row["nnb_ratio"] || 0) * 100).toFixed(1)}%</td>
                <td>${((row["vv_ratio"] || 0) * 100).toFixed(1)}%</td>
                <td>${((row["vx_verb_ratio"] || 0) * 100).toFixed(1)}%</td>
                <td>${((row["va_ratio"] || 0) * 100).toFixed(1)}%</td>
                <td>${((row["etm_ratio"] || 0) * 100).toFixed(1)}%</td>
                <td>${((row["etn_ratio"] || 0) * 100).toFixed(1)}%</td>
            `;
            workBasic2TableBody.appendChild(tr);
        });
    }

    function renderWorkModernTable(data) {
        workModernTableBody.innerHTML = "";
        data.forEach(row => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>${row["title"]}</strong></td>
                <td><strong class="clickable-author" data-author="${row["작가"]}">${row["작가"]}</strong></td>
                <td>${(row["semantic_flow"] || 0).toFixed(3)}</td>
                <td>${(row["semantic_diversity"] || 0).toFixed(3)}</td>
                <td>${(row["ppl"] || 0).toFixed(1)}</td>
                <td>${(row["lix"] || 0).toFixed(1)}</td>
                <td>${(row["network_density"] || 0).toFixed(3)}</td>
            `;
            workModernTableBody.appendChild(tr);
        });
    }

    // 작품별 기초 1 테이블 헤더 정렬 바인딩
    workBasicHeaders.forEach(th => {
        th.addEventListener("click", () => {
            const col = th.getAttribute("data-sort");
            if (!col) return;
            
            if (workBasicSortCol === col) {
                workBasicSortAsc = !workBasicSortAsc;
            } else {
                workBasicSortCol = col;
                workBasicSortAsc = true;
            }
            
            workBasicHeaders.forEach(h => h.querySelector("span").innerText = "↕");
            th.querySelector("span").innerText = workBasicSortAsc ? "▲" : "▼";
            
            const sortedData = [...ALL_WORKS].sort((a, b) => {
                const valA = a[col];
                const valB = b[col];
                if (typeof valA === "string") {
                    return workBasicSortAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
                }
                return workBasicSortAsc ? valA - valB : valB - valA;
            });
            renderWorkBasicTable(sortedData);
        });
    });

    // 작품별 기초 2 테이블 헤더 정렬 바인딩
    workBasic2Headers.forEach(th => {
        th.addEventListener("click", () => {
            const col = th.getAttribute("data-sort");
            if (!col) return;
            
            if (workBasic2SortCol === col) {
                workBasic2SortAsc = !workBasic2SortAsc;
            } else {
                workBasic2SortCol = col;
                workBasic2SortAsc = true;
            }
            
            workBasic2Headers.forEach(h => h.querySelector("span").innerText = "↕");
            th.querySelector("span").innerText = workBasic2SortAsc ? "▲" : "▼";
            
            const sortedData = [...ALL_WORKS].sort((a, b) => {
                const valA = a[col];
                const valB = b[col];
                if (typeof valA === "string") {
                    return workBasic2SortAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
                }
                return workBasic2SortAsc ? valA - valB : valB - valA;
            });
            renderWorkBasic2Table(sortedData);
        });
    });

    // 작품별 응용 분석 테이블 헤더 정렬 바인딩
    workModernHeaders.forEach(th => {
        th.addEventListener("click", () => {
            const col = th.getAttribute("data-sort");
            if (!col) return;
            
            if (workModernSortCol === col) {
                workModernSortAsc = !workModernSortAsc;
            } else {
                workModernSortCol = col;
                workModernSortAsc = true;
            }
            
            workModernHeaders.forEach(h => h.querySelector("span").innerText = "↕");
            th.querySelector("span").innerText = workModernSortAsc ? "▲" : "▼";
            
            const sortedData = [...ALL_WORKS].sort((a, b) => {
                const valA = a[col];
                const valB = b[col];
                if (typeof valA === "string") {
                    return workModernSortAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
                }
                return workModernSortAsc ? valA - valB : valB - valA;
            });
            renderWorkModernTable(sortedData);
        });
    });

    // 헤더 소팅 리스너 연동
    basicHeaders.forEach(th => {
        th.addEventListener("click", () => {
            const col = th.getAttribute("data-sort");
            if (!col) return;
            
            if (basicSortCol === col) {
                basicSortAsc = !basicSortAsc;
            } else {
                basicSortCol = col;
                basicSortAsc = true;
            }
            
            basicHeaders.forEach(h => h.querySelector("span").innerText = "↕");
            th.querySelector("span").innerText = basicSortAsc ? "▲" : "▼";
            
            const sortedData = [...BASIC_METRICS].sort((a, b) => {
                const valA = a[col];
                const valB = b[col];
                if (typeof valA === "string") {
                    return basicSortAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
                }
                return basicSortAsc ? valA - valB : valB - valA;
            });
            renderBasicTable(sortedData);
        });
    });

    basic2Headers.forEach(th => {
        th.addEventListener("click", () => {
            const col = th.getAttribute("data-sort");
            if (!col) return;
            
            if (basic2SortCol === col) {
                basic2SortAsc = !basic2SortAsc;
            } else {
                basic2SortCol = col;
                basic2SortAsc = true;
            }
            
            basic2Headers.forEach(h => h.querySelector("span").innerText = "↕");
            th.querySelector("span").innerText = basic2SortAsc ? "▲" : "▼";
            
            const sortedData = [...BASIC_METRICS].sort((a, b) => {
                const valA = a[col];
                const valB = b[col];
                if (typeof valA === "string") {
                    return basic2SortAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
                }
                return basic2SortAsc ? valA - valB : valB - valA;
            });
            renderBasic2Table(sortedData);
        });
    });

    modernHeaders.forEach(th => {
        th.addEventListener("click", () => {
            const col = th.getAttribute("data-sort");
            if (!col) return;
            if (!MODERN_METRICS || MODERN_METRICS.length === 0) return;
            
            if (modernSortCol === col) {
                modernSortAsc = !modernSortAsc;
            } else {
                modernSortCol = col;
                modernSortAsc = true;
            }
            
            modernHeaders.forEach(h => h.querySelector("span").innerText = "↕");
            th.querySelector("span").innerText = modernSortAsc ? "▲" : "▼";
            
            const sortedData = [...MODERN_METRICS].sort((a, b) => {
                const valA = a[col];
                const valB = b[col];
                if (typeof valA === "string") {
                    return modernSortAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
                }
                return modernSortAsc ? valA - valB : valB - valA;
            });
            renderModernTable(sortedData);
        });
    });

    // 9. 탭 활성화에 따른 동적 차트 로드
    function handleTabActivation(tabId) {
        if (tabId === "dashboard-tab") {
            renderDashboardHomeChart();
        } else if (tabId === "basic-tab") {
            renderBasicTabCharts();
        } else if (tabId === "modern-tab") {
            renderModernTabCharts();
        } else if (tabId === "author-tab") {
            triggerAuthorDetailUpdate();
        } else if (tabId === "compare-tab") {
            renderCompareRadarChart();
        }
    }

    // --- 차트 스타일 테마 헬퍼 ---
    function getChartThemeColors() {
        const isDark = currentTheme === "dark";
        return {
            text: isDark ? "#f3f4f6" : "#111827",
            grid: isDark ? "rgba(255, 255, 255, 0.06)" : "rgba(0, 0, 0, 0.05)",
            accent: "#7c3aed",
            accentGlow: isDark ? "rgba(124, 58, 237, 0.35)" : "rgba(109, 40, 217, 0.15)",
            palette: ["#8b5cf6", "#3b82f6", "#10b981", "#f59e0b", "#ec4899", "#06b6d4"]
        };
    }

    function updateAllChartsTheme() {
        Object.keys(charts).forEach(key => {
            if (charts[key]) {
                const colors = getChartThemeColors();
                if (charts[key].options.scales) {
                    Object.keys(charts[key].options.scales).forEach(scaleKey => {
                        const scale = charts[key].options.scales[scaleKey];
                        if (scale.ticks) scale.ticks.color = colors.text;
                        if (scale.grid) scale.grid.color = colors.grid;
                        if (scale.title) scale.title.color = colors.text;
                    });
                }
                if (charts[key].options.plugins && charts[key].options.plugins.legend) {
                    charts[key].options.plugins.legend.labels.color = colors.text;
                }
                charts[key].update();
            }
        });
    }

    // --- (1) 대시보드 홈 차트 ---
    function renderDashboardHomeChart() {
        const ctx = document.getElementById("home-summary-chart").getContext("2d");
        if (charts["homeSummary"]) {
            charts["homeSummary"].destroy();
        }
        
        const colors = getChartThemeColors();
        const scatterData = BASIC_METRICS.map(row => ({
            x: row["평균문장길이_자수"],
            y: row["어휘다양도_TTR"],
            label: row["작가"]
        }));

        charts["homeSummary"] = new Chart(ctx, {
            type: 'scatter',
            data: {
                datasets: [{
                    label: '작가별 문체 분포',
                    data: scatterData,
                    backgroundColor: colors.accent,
                    borderColor: '#ffffff',
                    borderWidth: 1,
                    pointRadius: 6,
                    pointHoverRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const p = context.raw;
                                return `${p.label} (평균문장자수: ${p.x.toFixed(1)}자, TTR: ${p.y.toFixed(3)})`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        title: { display: true, text: '평균 문장 길이 (자수)', color: colors.text, font: { weight: 'bold' } },
                        ticks: { color: colors.text },
                        grid: { color: colors.grid }
                    },
                    y: {
                        title: { display: true, text: '어휘 다양도 (TTR)', color: colors.text, font: { weight: 'bold' } },
                        ticks: { color: colors.text },
                        grid: { color: colors.grid }
                    }
                }
            }
        });
    }

    // --- (2) 기초 계량 탭 차트 ---
    function renderBasicTabCharts() {
        const ctxScatter = document.getElementById("basic-scatter-chart").getContext("2d");
        if (charts["basicScatter"]) charts["basicScatter"].destroy();
        
        const colors = getChartThemeColors();
        const scatterData = BASIC_METRICS.map(row => ({
            x: row["평균문장길이_자수"],
            y: row["평균어절길이_글자수"],
            label: row["작가"]
        }));

        charts["basicScatter"] = new Chart(ctxScatter, {
            type: 'scatter',
            data: {
                datasets: [{
                    label: '문장 자수 vs 어절 글자수',
                    data: scatterData,
                    backgroundColor: '#3b82f6',
                    borderColor: '#ffffff',
                    borderWidth: 1,
                    pointRadius: 6,
                    pointHoverRadius: 9
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const p = context.raw;
                                return `${p.label} (문장: ${p.x.toFixed(1)}자, 어절: ${p.y.toFixed(2)}자)`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        title: { display: true, text: '평균 문장 자수', color: colors.text, font: { weight: 'bold' } },
                        ticks: { color: colors.text },
                        grid: { color: colors.grid }
                    },
                    y: {
                        title: { display: true, text: '평균 어절 자수', color: colors.text, font: { weight: 'bold' } },
                        ticks: { color: colors.text },
                        grid: { color: colors.grid }
                    }
                }
            }
        });

        const ctxEnding = document.getElementById("basic-ending-chart").getContext("2d");
        if (charts["basicEnding"]) charts["basicEnding"].destroy();
        
        const sampleSize = 12;
        const sampleData = [...BASIC_METRICS].slice(0, sampleSize);
        const labels = sampleData.map(row => row["작가"]);
        const nounRatios = sampleData.map(row => row["명사형종결_비율"] * 100);
        const copulaRatios = sampleData.map(row => row["계사형종결_비율"] * 100);
        const verbRatios = sampleData.map(row => row["동사형종결_비율"] * 100);

        charts["basicEnding"] = new Chart(ctxEnding, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    { label: '동사형', data: verbRatios, backgroundColor: '#10b981' },
                    { label: '계사형', data: copulaRatios, backgroundColor: '#f59e0b' },
                    { label: '명사형', data: nounRatios, backgroundColor: '#8b5cf6' }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { stacked: true, ticks: { color: colors.text }, grid: { color: colors.grid } },
                    y: { stacked: true, max: 100, title: { display: true, text: '점유율 (%)', color: colors.text }, ticks: { color: colors.text }, grid: { color: colors.grid } }
                },
                plugins: {
                    legend: { labels: { color: colors.text } }
                }
            }
        });
    }

    // --- (3) 응용 분석 탭 차트 ---
    function renderModernTabCharts() {
        if (!MODERN_METRICS || MODERN_METRICS.length === 0) return;
        
        const ctxBubble = document.getElementById("modern-bubble-chart").getContext("2d");
        if (charts["modernBubble"]) charts["modernBubble"].destroy();
        
        const colors = getChartThemeColors();
        const bubbleData = MODERN_METRICS.map(row => ({
            x: row["가독성_LIX"],
            y: row["당혹도_PPL"],
            r: Math.max(3, row["버스트성_글자"] * 25), 
            label: row["작가"]
        }));

        charts["modernBubble"] = new Chart(ctxBubble, {
            type: 'bubble',
            data: {
                datasets: [{
                    label: '작가별 LIX-PPL 분포 (구 크기 = 버스트성)',
                    data: bubbleData,
                    backgroundColor: 'rgba(236, 72, 153, 0.6)',
                    borderColor: '#ec4899',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { color: colors.text } },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const p = context.raw;
                                return `${p.label} (가독성_LIX: ${p.x.toFixed(1)}, PPL: ${p.y.toFixed(1)}, 버스트성: ${(p.r/25).toFixed(3)})`;
                            }
                        }
                    }
                },
                scales: {
                    x: { title: { display: true, text: '가독성 (LIX 지표)', color: colors.text }, ticks: { color: colors.text }, grid: { color: colors.grid } },
                    y: { title: { display: true, text: '당혹도 (Perplexity)', color: colors.text }, ticks: { color: colors.text }, grid: { color: colors.grid } }
                }
            }
        });

        const ctxRadar = document.getElementById("modern-radar-chart").getContext("2d");
        if (charts["modernRadar"]) charts["modernRadar"].destroy();

        const targetAuthors = ["김동인", "김유정", "황순원"];
        const matchedRows = MODERN_METRICS.filter(row => targetAuthors.includes(row["작가"]));
        
        const features = ["의미흐름_유사도", "개념유사도_평균", "당혹도_PPL", "네트워크밀도", "가독성_LIX"];
        const maxValues = {};
        features.forEach(f => {
            maxValues[f] = Math.max(...MODERN_METRICS.map(row => row[f])) || 1.0;
        });

        const datasets = matchedRows.map((row, idx) => {
            const dataPoints = features.map(f => (row[f] / maxValues[f]) * 100);
            const strokeColor = colors.palette[idx];
            return {
                label: row["작가"],
                data: dataPoints,
                backgroundColor: strokeColor + "20",
                borderColor: strokeColor,
                borderWidth: 2,
                pointBackgroundColor: strokeColor
            };
        });

        charts["modernRadar"] = new Chart(ctxRadar, {
            type: 'radar',
            data: {
                labels: ["의미 흐름", "개념 다양성", "당혹도 (PPL)", "네트워크 밀도", "가독성 (LIX)"],
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        grid: { color: colors.grid },
                        angleLines: { color: colors.grid },
                        ticks: { color: colors.text, backdropColor: 'transparent' },
                        pointLabels: { color: colors.text, font: { size: 12, weight: 'bold' } },
                        min: 0,
                        max: 100
                    }
                },
                plugins: {
                    legend: { labels: { color: colors.text } }
                }
            }
        });
    }

    // --- (4) 작가별 상세 프로파일 동적 갱신 ---
    function triggerAuthorDetailUpdate() {
        const selectedAuthor = authorSelect.value;
        if (!selectedAuthor || !AUTHOR_DETAILS[selectedAuthor]) {
            authorDetailsContainer.style.display = "none";
            return;
        }

        authorDetailsContainer.style.display = "grid";
        
        const details = AUTHOR_DETAILS[selectedAuthor];
        const basicData = details.basic;
        const modernData = details.modern;

        document.getElementById("detail-author-name").innerText = selectedAuthor;
        document.getElementById("detail-works-count").innerText = basicData.metadata.total_works || 0;
        
        const avgSent = basicData.sentence_statistics.sentence_char_stats.mean || 0;
        document.getElementById("detail-avg-sent-len").innerText = `${avgSent.toFixed(1)}자`;
        
        const ttrVal = basicData.lexical_statistics.average_ttr || 0;
        document.getElementById("detail-ttr").innerText = ttrVal.toFixed(3);
        
        const lixVal = modernData.가독성_LIX || 0;
        document.getElementById("detail-lix").innerText = lixVal.toFixed(1);
        
        const pplVal = modernData.당혹도_PPL || 0;
        document.getElementById("detail-ppl").innerText = pplVal.toFixed(1);

        const endingsContainer = document.getElementById("detail-top-endings");
        endingsContainer.innerHTML = "";
        const topEndings = Object.entries(basicData.specialized_statistics.ending_morphemes || {}).slice(0, 8);
        
        if (topEndings.length > 0) {
            topEndings.forEach(([morph, freq]) => {
                const badge = document.createElement("span");
                badge.className = "ending-badge";
                badge.innerHTML = `<strong>${morph}</strong> (${freq}회)`;
                endingsContainer.appendChild(badge);
            });
        } else {
            endingsContainer.innerHTML = `<span style="color:var(--text-secondary);">정보 없음</span>`;
        }

        const ctxPos = document.getElementById("detail-pos-chart").getContext("2d");
        if (charts["authorDetailPos"]) charts["authorDetailPos"].destroy();

        const colors = getChartThemeColors();
        const posRatios = basicData.pos_ratios || {};
        const posLabels = ["명사", "동사", "형용사", "조사", "어미", "수식언"];
        const posValues = [
            (posRatios.nouns_ratio || 0) * 100,
            (posRatios.verbs_ratio || 0) * 100,
            (posRatios.adjectives_ratio || 0) * 100,
            (posRatios.particles_ratio || 0) * 100,
            (posRatios.endings_ratio || 0) * 100,
            (posRatios.modifiers_ratio || 0) * 100
        ];

        charts["authorDetailPos"] = new Chart(ctxPos, {
            type: 'doughnut',
            data: {
                labels: posLabels,
                datasets: [{
                    data: posValues,
                    backgroundColor: colors.palette,
                    borderColor: 'transparent'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: { color: colors.text, boxWidth: 12 }
                    }
                }
            }
        });

        const ctxEnd = document.getElementById("detail-ending-chart").getContext("2d");
        if (charts["authorDetailEnding"]) charts["authorDetailEnding"].destroy();

        const endingData = basicData.sentence_ending_statistics || {};
        const endingLabels = ["명사형", "계사형", "동사형", "기타"];
        const endingValues = [
            (endingData.noun_style_ratio || 0) * 100,
            (endingData.copula_style_ratio || 0) * 100,
            (endingData.verb_style_ratio || 0) * 100,
            (endingData.other_style_ratio || 0) * 100
        ];

        charts["authorDetailEnding"] = new Chart(ctxEnd, {
            type: 'polarArea',
            data: {
                labels: endingLabels,
                datasets: [{
                    data: endingValues,
                    backgroundColor: ["#8b5cf6", "#f59e0b", "#10b981", "#9ca3af"]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        ticks: { display: false },
                        grid: { color: colors.grid }
                    }
                },
                plugins: {
                    legend: {
                        position: 'right',
                        labels: { color: colors.text, boxWidth: 12 }
                    }
                }
            }
        });
    }

    // --- (5) 작가별 다차원 비교 탭 작동 및 동적 레이더 차트 렌더링 ---
    function initCompareTabSelectors() {
        compareAuthorChipsContainer.innerHTML = "";
        compareMetricChipsContainer.innerHTML = "";

        // 작가 칩 렌더링
        BASIC_METRICS.forEach(row => {
            const author = row["작가"];
            const chip = document.createElement("div");
            chip.className = `chip ${selectedCompareAuthors.includes(author) ? 'active' : ''}`;
            chip.innerText = author;
            chip.addEventListener("click", () => {
                if (selectedCompareAuthors.includes(author)) {
                    // 선택 해제
                    selectedCompareAuthors = selectedCompareAuthors.filter(a => a !== author);
                    chip.classList.remove("active");
                } else {
                    // 선택 추가
                    selectedCompareAuthors.push(author);
                    chip.classList.add("active");
                }
                renderCompareRadarChart();
            });
            compareAuthorChipsContainer.appendChild(chip);
        });

        // 지표 칩 렌더링
        COMPARE_METRIC_METADATA.forEach(metric => {
            const chip = document.createElement("div");
            chip.className = `chip ${selectedCompareMetrics.includes(metric.key) ? 'active' : ''}`;
            chip.innerText = metric.label;
            chip.addEventListener("click", () => {
                if (selectedCompareMetrics.includes(metric.key)) {
                    // 선택 해제
                    selectedCompareMetrics = selectedCompareMetrics.filter(m => m !== metric.key);
                    chip.classList.remove("active");
                } else {
                    // 선택 추가 (제한 없음)
                    selectedCompareMetrics.push(metric.key);
                    chip.classList.add("active");
                }
                renderCompareRadarChart();
            });
            compareMetricChipsContainer.appendChild(chip);
        });
    }

    function renderCompareRadarChart() {
        const ctx = document.getElementById("compare-radar-chart").getContext("2d");
        if (charts["compareRadar"]) charts["compareRadar"].destroy();

        const colors = getChartThemeColors();

        // 1. 선택 데이터 무결성 검증
        if (selectedCompareAuthors.length === 0 || selectedCompareMetrics.length === 0) {
            // 빈 영역 처리
            ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
            return;
        }

        // 2. 축 라벨 설정 (선택된 지표들의 라벨 목록)
        const metricLabels = selectedCompareMetrics.map(key => {
            const meta = COMPARE_METRIC_METADATA.find(m => m.key === key);
            return meta ? meta.label : key;
        });

        // 3. 각 작가별 지표 표준화 데이터셋 매핑
        const datasets = selectedCompareAuthors.map((authorName, idx) => {
            // 해당 작가의 데이터 로드
            const basicRow = BASIC_METRICS.find(r => r["작가"] === authorName) || {};
            const modernRow = (MODERN_METRICS || []).find(r => r["작가"] === authorName) || {};
            
            // 모든 지표를 하나로 머지
            const mergedMetrics = { ...basicRow, ...modernRow };

            // 지표별 최소-최대 정규화 (Min-Max Normalization) 기반 급간 차이 극대화 스케일링
            const scaledData = selectedCompareMetrics.map(key => {
                const value = mergedMetrics[key] || 0.0;
                
                // 전체 데이터셋에서 해당 지표의 최소값 및 최대값 동적 산출
                let maxVal = -Infinity;
                let minVal = Infinity;
                BASIC_METRICS.forEach(r => {
                    if (r[key] !== undefined) {
                        if (r[key] > maxVal) maxVal = r[key];
                        if (r[key] < minVal) minVal = r[key];
                    }
                });
                if (MODERN_METRICS) {
                    MODERN_METRICS.forEach(r => {
                        if (r[key] !== undefined) {
                            if (r[key] > maxVal) maxVal = r[key];
                            if (r[key] < minVal) minVal = r[key];
                        }
                    });
                }
                
                // 방어 코드
                if (maxVal === -Infinity) maxVal = 1.0;
                if (minVal === Infinity) minVal = 0.0;
                
                // 최소값을 5%, 최대값을 95%로 매핑하여 급간 차이를 극대화하고 오각형 틀 이탈 방지
                const minPercent = 5;
                const maxPercent = 95;
                
                let scaledValue = minPercent;
                if (maxVal > minVal) {
                    scaledValue = minPercent + ((value - minVal) / (maxVal - minVal)) * (maxPercent - minPercent);
                }
                return scaledValue;
            });

            const strokeColor = colors.palette[idx % colors.palette.length];
            return {
                label: authorName,
                data: scaledData,
                backgroundColor: strokeColor + "15",
                borderColor: strokeColor,
                borderWidth: 2,
                pointBackgroundColor: strokeColor,
                pointRadius: 4
            };
        });

        charts["compareRadar"] = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: metricLabels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        grid: { color: colors.grid },
                        angleLines: { color: colors.grid },
                        ticks: { 
                            display: true,
                            color: colors.text, 
                            backdropColor: 'transparent',
                            font: { size: 10 },
                            stepSize: 20
                        },
                        pointLabels: { 
                            color: colors.text, 
                            font: { size: 12, weight: 'bold' } 
                        },
                        min: 0,
                        max: 100
                    }
                },
                plugins: {
                    legend: { 
                        position: 'top',
                        labels: { color: colors.text, font: { size: 13, weight: 'bold' } } 
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const author = context.dataset.label;
                                const metricKey = selectedCompareMetrics[context.dataIndex];
                                
                                // 실제 리얼 원본 수치 구하기
                                const basicRow = BASIC_METRICS.find(r => r["작가"] === author) || {};
                                const modernRow = (MODERN_METRICS || []).find(r => r["작가"] === author) || {};
                                const merged = { ...basicRow, ...modernRow };
                                const originalValue = merged[metricKey];
                                
                                const originalStr = typeof originalValue === "number" ? 
                                    (originalValue < 1.0 ? originalValue.toFixed(3) : originalValue.toFixed(1)) : 
                                    originalValue;
                                
                                return `${author}: ${originalStr} (상대적 백분율: ${context.raw.toFixed(1)}%)`;
                            }
                        }
                    }
                }
            }
        });
    }

    authorSelect.addEventListener("change", triggerAuthorDetailUpdate);

    // 10. 초기 데이터 주입 및 가동
    function init() {
        renderGuide();

        // 1. 전체 작품 평탄화 목록(ALL_WORKS) 구축
        ALL_WORKS = [];
        Object.keys(AUTHOR_DETAILS).forEach(authorName => {
            const authorData = AUTHOR_DETAILS[authorName];
            if (authorData && authorData.works) {
                authorData.works.forEach(work => {
                    ALL_WORKS.push({
                        "작가": authorName,
                        ...work
                    });
                });
            }
        });
        
        renderBasicTable(BASIC_METRICS);
        renderBasic2Table(BASIC_METRICS);
        renderModernTable(MODERN_METRICS);

        // 작품별 테이블 렌더링
        renderWorkBasicTable(ALL_WORKS);
        renderWorkBasic2Table(ALL_WORKS);
        renderWorkModernTable(ALL_WORKS);
        
        // 작가 선택 드롭다운 채우기
        authorSelect.innerHTML = "";
        BASIC_METRICS.forEach(row => {
            const opt = document.createElement("option");
            opt.value = row["작가"];
            opt.innerText = row["작가"];
            authorSelect.appendChild(opt);
        });

        // 작가별 다차원 비교 탭 칩 빌드 및 정렬 바인딩
        initCompareTabSelectors();
        
        handleTabActivation(activeTab);
    }
    
    init();
});

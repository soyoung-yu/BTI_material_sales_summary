// 소재 데이터 (나중에 내부 DB에서 관리 예정)
const MATERIALS = [
    { raw_cd: "M-1001", raw_nm: "AURORA PEPTIDE", mmsta: "NO", researcher: "홍길동", created: "2025-10-01" },
    { raw_cd: "M-1002", raw_nm: "SOLAR BIOME", mmsta: "YES", researcher: "김연아", created: "2025-10-10" },
    { raw_cd: "M-1003", raw_nm: "RIVER CICA", mmsta: "NO", researcher: "박지성", created: "2025-11-02" },
    { raw_cd: "M-1004", raw_nm: "CLOUD COLLAGEN", mmsta: "NO", researcher: "이순신", created: "2025-11-12" },
    { raw_cd: "M-1005", raw_nm: "NOVA CERAMIDE", mmsta: "YES", researcher: "유관순", created: "2025-11-20" },
    { raw_cd: "M-1006", raw_nm: "FOREST PROBIOME", mmsta: "NO", researcher: "장영실", created: "2025-12-01" },
    { raw_cd: "M-1007", raw_nm: "POLAR HYALURON", mmsta: "NO", researcher: "신사임당", created: "2025-12-12" },
    { raw_cd: "M-1008", raw_nm: "SPARK VIT-C", mmsta: "YES", researcher: "세종", created: "2025-12-18" },
    { raw_cd: "M-1009", raw_nm: "TWILIGHT NIACIN", mmsta: "NO", researcher: "허준", created: "2026-01-05" },
    { raw_cd: "M-1010", raw_nm: "BREEZE PANTHENOL", mmsta: "NO", researcher: "윤봉길", created: "2026-01-15" }
];

// 샘플 데이터 - sample_df.csv에서 자동 생성

const RAW_SALES_DATA = [
    { raw_cd: "M-1001", raw_nm: "AURORA PEPTIDE", raw_ratio: 0.002, mitem_code: "P-2001", mitem_name: "라이트닝 세럼 30ML", category: "FERT", forml_code: "11S0703", forml_name: "앰플", customer_code: "C-3101", customer_name: "루미너스코", base_time: "2024-03-01", total_revenue: 9100000.0, product_sales_revenue: 9100000.0, net_revenue: 4100000.0, product_name: "라이트닝 세럼" },
    { raw_cd: "M-1001", raw_nm: "AURORA PEPTIDE", raw_ratio: 0.002, mitem_code: "P-2001", mitem_name: "라이트닝 세럼 30ML", category: "FERT", forml_code: "11S0703", forml_name: "앰플", customer_code: "C-3101", customer_name: "루미너스코", base_time: "2025-07-01", total_revenue: 10300000.0, product_sales_revenue: 10300000.0, net_revenue: 4700000.0, product_name: "라이트닝 세럼" },
    { raw_cd: "M-1001", raw_nm: "AURORA PEPTIDE", raw_ratio: 0.002, mitem_code: "P-2001", mitem_name: "라이트닝 세럼 30ML", category: "FERT", forml_code: "11S0703", forml_name: "앰플", customer_code: "C-3101", customer_name: "루미너스코", base_time: "2025-10-01", total_revenue: 12450000.0, product_sales_revenue: 12450000.0, net_revenue: 5600000.0, product_name: "라이트닝 세럼" },
    { raw_cd: "M-1001", raw_nm: "AURORA PEPTIDE", raw_ratio: 0.002, mitem_code: "P-2001", mitem_name: "라이트닝 세럼 30ML", category: "FERT", forml_code: "11S0703", forml_name: "앰플", customer_code: "C-3101", customer_name: "루미너스코", base_time: "2025-11-01", total_revenue: 9800000.0, product_sales_revenue: 9800000.0, net_revenue: 4300000.0, product_name: "라이트닝 세럼" },

    { raw_cd: "M-1002", raw_nm: "SOLAR BIOME", raw_ratio: 0.015, mitem_code: "P-2002", mitem_name: "모이스처 크림 50ML", category: "FERT", forml_code: "11S0301", forml_name: "크림", customer_code: "C-3102", customer_name: "소프트랩", base_time: "2024-06-01", total_revenue: 17200000.0, product_sales_revenue: 17200000.0, net_revenue: 7600000.0, product_name: "모이스처 크림" },
    { raw_cd: "M-1002", raw_nm: "SOLAR BIOME", raw_ratio: 0.015, mitem_code: "P-2002", mitem_name: "모이스처 크림 50ML", category: "FERT", forml_code: "11S0301", forml_name: "크림", customer_code: "C-3102", customer_name: "소프트랩", base_time: "2025-08-01", total_revenue: 20100000.0, product_sales_revenue: 20100000.0, net_revenue: 9000000.0, product_name: "모이스처 크림" },
    { raw_cd: "M-1002", raw_nm: "SOLAR BIOME", raw_ratio: 0.015, mitem_code: "P-2002", mitem_name: "모이스처 크림 50ML", category: "FERT", forml_code: "11S0301", forml_name: "크림", customer_code: "C-3102", customer_name: "소프트랩", base_time: "2025-10-01", total_revenue: 21500000.0, product_sales_revenue: 21500000.0, net_revenue: 9600000.0, product_name: "모이스처 크림" },
    { raw_cd: "M-1002", raw_nm: "SOLAR BIOME", raw_ratio: 0.015, mitem_code: "P-2002", mitem_name: "모이스처 크림 50ML", category: "FERT", forml_code: "11S0301", forml_name: "크림", customer_code: "C-3102", customer_name: "소프트랩", base_time: "2025-12-01", total_revenue: 18300000.0, product_sales_revenue: 18300000.0, net_revenue: 8200000.0, product_name: "모이스처 크림" },

    { raw_cd: "M-1003", raw_nm: "RIVER CICA", raw_ratio: 0.008, mitem_code: "P-2003", mitem_name: "시카 젤 80ML", category: "FERT", forml_code: "11S0401", forml_name: "젤", customer_code: "C-3103", customer_name: "리버뷰", base_time: "2024-02-01", total_revenue: 12100000.0, product_sales_revenue: 12100000.0, net_revenue: 5200000.0, product_name: "시카 젤" },
    { raw_cd: "M-1003", raw_nm: "RIVER CICA", raw_ratio: 0.008, mitem_code: "P-2003", mitem_name: "시카 젤 80ML", category: "FERT", forml_code: "11S0401", forml_name: "젤", customer_code: "C-3103", customer_name: "리버뷰", base_time: "2025-11-01", total_revenue: 14200000.0, product_sales_revenue: 14200000.0, net_revenue: 6100000.0, product_name: "시카 젤" },
    { raw_cd: "M-1003", raw_nm: "RIVER CICA", raw_ratio: 0.008, mitem_code: "P-2003", mitem_name: "시카 젤 80ML", category: "FERT", forml_code: "11S0401", forml_name: "젤", customer_code: "C-3103", customer_name: "리버뷰", base_time: "2025-09-01", total_revenue: 15500000.0, product_sales_revenue: 15500000.0, net_revenue: 6800000.0, product_name: "시카 젤" },

    { raw_cd: "M-1004", raw_nm: "CLOUD COLLAGEN", raw_ratio: 0.020, mitem_code: "P-2004", mitem_name: "클라우드 마스크 5매", category: "FERT", forml_code: "11S1004", forml_name: "마스크시트", customer_code: "C-3104", customer_name: "스카이메드", base_time: "2024-09-01", total_revenue: 6800000.0, product_sales_revenue: 6800000.0, net_revenue: 2800000.0, product_name: "클라우드 마스크" },
    { raw_cd: "M-1004", raw_nm: "CLOUD COLLAGEN", raw_ratio: 0.020, mitem_code: "P-2004", mitem_name: "클라우드 마스크 5매", category: "FERT", forml_code: "11S1004", forml_name: "마스크시트", customer_code: "C-3104", customer_name: "스카이메드", base_time: "2025-07-01", total_revenue: 7200000.0, product_sales_revenue: 7200000.0, net_revenue: 3000000.0, product_name: "클라우드 마스크" },
    { raw_cd: "M-1004", raw_nm: "CLOUD COLLAGEN", raw_ratio: 0.020, mitem_code: "P-2004", mitem_name: "클라우드 마스크 5매", category: "FERT", forml_code: "11S1004", forml_name: "마스크시트", customer_code: "C-3104", customer_name: "스카이메드", base_time: "2025-10-01", total_revenue: 7600000.0, product_sales_revenue: 7600000.0, net_revenue: 3100000.0, product_name: "클라우드 마스크" },
    { raw_cd: "M-1004", raw_nm: "CLOUD COLLAGEN", raw_ratio: 0.020, mitem_code: "P-2004", mitem_name: "클라우드 마스크 5매", category: "FERT", forml_code: "11S1004", forml_name: "마스크시트", customer_code: "C-3104", customer_name: "스카이메드", base_time: "2025-12-01", total_revenue: 8900000.0, product_sales_revenue: 8900000.0, net_revenue: 3600000.0, product_name: "클라우드 마스크" },

    { raw_cd: "M-1005", raw_nm: "NOVA CERAMIDE", raw_ratio: 0.004, mitem_code: "P-2005", mitem_name: "나이트 리페어 크림 60ML", category: "FERT", forml_code: "11S0301", forml_name: "크림", customer_code: "C-3105", customer_name: "노바케어", base_time: "2024-05-01", total_revenue: 16200000.0, product_sales_revenue: 16200000.0, net_revenue: 7200000.0, product_name: "나이트 리페어 크림" },
    { raw_cd: "M-1005", raw_nm: "NOVA CERAMIDE", raw_ratio: 0.004, mitem_code: "P-2005", mitem_name: "나이트 리페어 크림 60ML", category: "FERT", forml_code: "11S0301", forml_name: "크림", customer_code: "C-3105", customer_name: "노바케어", base_time: "2025-08-01", total_revenue: 18700000.0, product_sales_revenue: 18700000.0, net_revenue: 8400000.0, product_name: "나이트 리페어 크림" },
    { raw_cd: "M-1005", raw_nm: "NOVA CERAMIDE", raw_ratio: 0.004, mitem_code: "P-2005", mitem_name: "나이트 리페어 크림 60ML", category: "FERT", forml_code: "11S0301", forml_name: "크림", customer_code: "C-3105", customer_name: "노바케어", base_time: "2025-11-01", total_revenue: 19800000.0, product_sales_revenue: 19800000.0, net_revenue: 8900000.0, product_name: "나이트 리페어 크림" },

    { raw_cd: "M-1006", raw_nm: "FOREST PROBIOME", raw_ratio: 0.003, mitem_code: "P-2006", mitem_name: "리프레시 토너 200ML", category: "FERT", forml_code: "11S1009", forml_name: "마스크 패드", customer_code: "C-3106", customer_name: "포레스트랩", base_time: "2024-01-01", total_revenue: 4700000.0, product_sales_revenue: 4700000.0, net_revenue: 2100000.0, product_name: "리프레시 토너" },
    { raw_cd: "M-1006", raw_nm: "FOREST PROBIOME", raw_ratio: 0.003, mitem_code: "P-2006", mitem_name: "리프레시 토너 200ML", category: "FERT", forml_code: "11S1009", forml_name: "마스크 패드", customer_code: "C-3106", customer_name: "포레스트랩", base_time: "2025-12-01", total_revenue: 5400000.0, product_sales_revenue: 5400000.0, net_revenue: 2500000.0, product_name: "리프레시 토너" },
    { raw_cd: "M-1006", raw_nm: "FOREST PROBIOME", raw_ratio: 0.003, mitem_code: "P-2006", mitem_name: "리프레시 토너 200ML", category: "FERT", forml_code: "11S1009", forml_name: "마스크 패드", customer_code: "C-3106", customer_name: "포레스트랩", base_time: "2025-09-01", total_revenue: 6100000.0, product_sales_revenue: 6100000.0, net_revenue: 2800000.0, product_name: "리프레시 토너" },

    { raw_cd: "M-1007", raw_nm: "POLAR HYALURON", raw_ratio: 0.007, mitem_code: "P-2007", mitem_name: "하이드라 수분 에센스 50ML", category: "FERT", forml_code: "11S0701", forml_name: "에센스", customer_code: "C-3107", customer_name: "폴라뷰티", base_time: "2024-07-01", total_revenue: 11800000.0, product_sales_revenue: 11800000.0, net_revenue: 5200000.0, product_name: "하이드라 수분 에센스" },
    { raw_cd: "M-1007", raw_nm: "POLAR HYALURON", raw_ratio: 0.007, mitem_code: "P-2007", mitem_name: "하이드라 수분 에센스 50ML", category: "FERT", forml_code: "11S0701", forml_name: "에센스", customer_code: "C-3107", customer_name: "폴라뷰티", base_time: "2025-10-01", total_revenue: 12600000.0, product_sales_revenue: 12600000.0, net_revenue: 5600000.0, product_name: "하이드라 수분 에센스" },
    { raw_cd: "M-1007", raw_nm: "POLAR HYALURON", raw_ratio: 0.007, mitem_code: "P-2007", mitem_name: "하이드라 수분 에센스 50ML", category: "FERT", forml_code: "11S0701", forml_name: "에센스", customer_code: "C-3107", customer_name: "폴라뷰티", base_time: "2025-12-01", total_revenue: 13200000.0, product_sales_revenue: 13200000.0, net_revenue: 5900000.0, product_name: "하이드라 수분 에센스" },

    { raw_cd: "M-1008", raw_nm: "SPARK VIT-C", raw_ratio: 0.001, mitem_code: "P-2008", mitem_name: "브라이트 필링 토너 150ML", category: "FERT", forml_code: "11S0101", forml_name: "토너", customer_code: "C-3108", customer_name: "스파크랩", base_time: "2024-04-01", total_revenue: 6500000.0, product_sales_revenue: 6500000.0, net_revenue: 2500000.0, product_name: "브라이트 필링 토너" },
    { raw_cd: "M-1008", raw_nm: "SPARK VIT-C", raw_ratio: 0.001, mitem_code: "P-2008", mitem_name: "브라이트 필링 토너 150ML", category: "FERT", forml_code: "11S0101", forml_name: "토너", customer_code: "C-3108", customer_name: "스파크랩", base_time: "2025-10-01", total_revenue: 7200000.0, product_sales_revenue: 7200000.0, net_revenue: 2800000.0, product_name: "브라이트 필링 토너" },
    { raw_cd: "M-1008", raw_nm: "SPARK VIT-C", raw_ratio: 0.001, mitem_code: "P-2008", mitem_name: "브라이트 필링 토너 150ML", category: "FERT", forml_code: "11S0101", forml_name: "토너", customer_code: "C-3108", customer_name: "스파크랩", base_time: "2025-08-01", total_revenue: 7900000.0, product_sales_revenue: 7900000.0, net_revenue: 3100000.0, product_name: "브라이트 필링 토너" },

    { raw_cd: "M-1009", raw_nm: "TWILIGHT NIACIN", raw_ratio: 0.006, mitem_code: "P-2009", mitem_name: "톤업 선스크린 50ML", category: "FERT", forml_code: "11S1301", forml_name: "선크림(스킨케어)", customer_code: "C-3109", customer_name: "트와이라이트", base_time: "2024-11-01", total_revenue: 13800000.0, product_sales_revenue: 13800000.0, net_revenue: 5900000.0, product_name: "톤업 선스크린" },
    { raw_cd: "M-1009", raw_nm: "TWILIGHT NIACIN", raw_ratio: 0.006, mitem_code: "P-2009", mitem_name: "톤업 선스크린 50ML", category: "FERT", forml_code: "11S1301", forml_name: "선크림(스킨케어)", customer_code: "C-3109", customer_name: "트와이라이트", base_time: "2025-07-01", total_revenue: 14700000.0, product_sales_revenue: 14700000.0, net_revenue: 6200000.0, product_name: "톤업 선스크린" },

    { raw_cd: "M-1010", raw_nm: "BREEZE PANTHENOL", raw_ratio: 0.005, mitem_code: "P-2010", mitem_name: "수딩 로션 120ML", category: "FERT", forml_code: "11S1302", forml_name: "선로션(스킨케어)", customer_code: "C-3110", customer_name: "브리즈코", base_time: "2024-12-01", total_revenue: 9800000.0, product_sales_revenue: 9800000.0, net_revenue: 4200000.0, product_name: "수딩 로션" },
    { raw_cd: "M-1010", raw_nm: "BREEZE PANTHENOL", raw_ratio: 0.005, mitem_code: "P-2010", mitem_name: "수딩 로션 120ML", category: "FERT", forml_code: "11S1302", forml_name: "선로션(스킨케어)", customer_code: "C-3110", customer_name: "브리즈코", base_time: "2025-08-01", total_revenue: 10600000.0, product_sales_revenue: 10600000.0, net_revenue: 4600000.0, product_name: "수딩 로션" }
];

// 샘플 데이터 확장 (기간 범위 유지, 기간별 +50행)
const EXTRA_BASE_TIMES = [
    "2024-01-01",
    "2024-02-01",
    "2024-03-01",
    "2024-04-01",
    "2024-05-01",
    "2024-06-01",
    "2024-07-01",
    "2024-09-01",
    "2024-11-01",
    "2024-12-01",
    "2025-07-01",
    "2025-08-01",
    "2025-09-01",
    "2025-10-01",
    "2025-11-01",
    "2025-12-01"
];

const MATERIAL_POOL = [
    { raw_cd: "M-1001", raw_nm: "AURORA PEPTIDE", raw_ratio: 0.002 },
    { raw_cd: "M-1002", raw_nm: "SOLAR BIOME", raw_ratio: 0.015 },
    { raw_cd: "M-1003", raw_nm: "RIVER CICA", raw_ratio: 0.008 },
    { raw_cd: "M-1004", raw_nm: "CLOUD COLLAGEN", raw_ratio: 0.02 },
    { raw_cd: "M-1005", raw_nm: "NOVA CERAMIDE", raw_ratio: 0.004 },
    { raw_cd: "M-1006", raw_nm: "FOREST PROBIOME", raw_ratio: 0.003 },
    { raw_cd: "M-1007", raw_nm: "POLAR HYALURON", raw_ratio: 0.007 },
    { raw_cd: "M-1008", raw_nm: "SPARK VIT-C", raw_ratio: 0.001 },
    { raw_cd: "M-1009", raw_nm: "TWILIGHT NIACIN", raw_ratio: 0.006 },
    { raw_cd: "M-1010", raw_nm: "BREEZE PANTHENOL", raw_ratio: 0.005 }
];

const CUSTOMER_POOL = [
    { customer_code: "C-3101", customer_name: "루미너스코" },
    { customer_code: "C-3102", customer_name: "소프트랩" },
    { customer_code: "C-3103", customer_name: "리버뷰" },
    { customer_code: "C-3104", customer_name: "스카이메드" },
    { customer_code: "C-3105", customer_name: "노바케어" },
    { customer_code: "C-3106", customer_name: "포레스트랩" },
    { customer_code: "C-3107", customer_name: "폴라뷰티" },
    { customer_code: "C-3108", customer_name: "스파크랩" },
    { customer_code: "C-3109", customer_name: "트와이라이트" },
    { customer_code: "C-3110", customer_name: "브리즈코" },
    // 추가 고객 +5
    { customer_code: "C-3111", customer_name: "오로라웍스" },
    { customer_code: "C-3112", customer_name: "벨벳코" },
    { customer_code: "C-3113", customer_name: "코즈모텍" },
    { customer_code: "C-3114", customer_name: "네오스킨" },
    { customer_code: "C-3115", customer_name: "루나랩" }
];

const PRODUCT_POOL = [
    { mitem_code: "P-2001", mitem_name: "라이트닝 세럼 30ML", product_name: "라이트닝 세럼", category: "FERT", forml_code: "11S0703", forml_name: "앰플" },
    { mitem_code: "P-2002", mitem_name: "모이스처 크림 50ML", product_name: "모이스처 크림", category: "FERT", forml_code: "11S0301", forml_name: "크림" },
    { mitem_code: "P-2003", mitem_name: "시카 젤 80ML", product_name: "시카 젤", category: "FERT", forml_code: "11S0401", forml_name: "젤" },
    { mitem_code: "P-2004", mitem_name: "클라우드 마스크 5매", product_name: "클라우드 마스크", category: "FERT", forml_code: "11S1004", forml_name: "마스크시트" },
    { mitem_code: "P-2005", mitem_name: "나이트 리페어 크림 60ML", product_name: "나이트 리페어 크림", category: "FERT", forml_code: "11S0301", forml_name: "크림" },
    { mitem_code: "P-2006", mitem_name: "리프레시 토너 200ML", product_name: "리프레시 토너", category: "FERT", forml_code: "11S1009", forml_name: "마스크 패드" },
    { mitem_code: "P-2007", mitem_name: "하이드라 수분 에센스 50ML", product_name: "하이드라 수분 에센스", category: "FERT", forml_code: "11S0701", forml_name: "에센스" },
    { mitem_code: "P-2008", mitem_name: "브라이트 필링 토너 150ML", product_name: "브라이트 필링 토너", category: "FERT", forml_code: "11S0101", forml_name: "토너" },
    { mitem_code: "P-2009", mitem_name: "톤업 선스크린 50ML", product_name: "톤업 선스크린", category: "FERT", forml_code: "11S1301", forml_name: "선크림(스킨케어)" },
    { mitem_code: "P-2010", mitem_name: "수딩 로션 120ML", product_name: "수딩 로션", category: "FERT", forml_code: "11S1302", forml_name: "선로션(스킨케어)" },
    // 추가 제품 +5
    { mitem_code: "P-2011", mitem_name: "글로우 에센스 45ML", product_name: "글로우 에센스", category: "FERT", forml_code: "11S0701", forml_name: "에센스" },
    { mitem_code: "P-2012", mitem_name: "리바이탈 크림 50ML", product_name: "리바이탈 크림", category: "FERT", forml_code: "11S0301", forml_name: "크림" },
    { mitem_code: "P-2013", mitem_name: "캄 다운 젤 70ML", product_name: "캄 다운 젤", category: "FERT", forml_code: "11S0401", forml_name: "젤" },
    { mitem_code: "P-2014", mitem_name: "모이스트 미스트 120ML", product_name: "모이스트 미스트", category: "FERT", forml_code: "11S0102", forml_name: "미스트" },
    { mitem_code: "P-2015", mitem_name: "리커버 마스크 5매", product_name: "리커버 마스크", category: "FERT", forml_code: "11S1004", forml_name: "마스크시트" }
];

const GENERATED_ROWS = [];
let seed = 42;
function rand() {
    seed = (seed * 9301 + 49297) % 233280;
    return seed / 233280;
}

EXTRA_BASE_TIMES.forEach((baseTime, monthIndex) => {
    for (let i = 0; i < 50; i += 1) {
        const material = MATERIAL_POOL[(i + monthIndex) % MATERIAL_POOL.length];
        const product = PRODUCT_POOL[(i * 3 + monthIndex) % PRODUCT_POOL.length];
        const customer = CUSTOMER_POOL[(i * 7 + monthIndex) % CUSTOMER_POOL.length];

        const salesBase = 5000000 + Math.floor(rand() * 18000000);
        const sales = Math.round(salesBase / 1000) * 1000;
        const margin = 0.35 + rand() * 0.25;
        const net = Math.round(sales * margin / 1000) * 1000;

        GENERATED_ROWS.push({
            raw_cd: material.raw_cd,
            raw_nm: material.raw_nm,
            raw_ratio: material.raw_ratio,
            mitem_code: product.mitem_code,
            mitem_name: product.mitem_name,
            category: product.category,
            forml_code: product.forml_code,
            forml_name: product.forml_name,
            customer_code: customer.customer_code,
            customer_name: customer.customer_name,
            base_time: baseTime,
            total_revenue: sales,
            product_sales_revenue: sales,
            net_revenue: net,
            product_name: product.product_name
        });
    }
});

RAW_SALES_DATA.push(...GENERATED_ROWS);

// 집계 함수들

// 숫자 포맷팅
function formatNumber(num) {
    return new Intl.NumberFormat('ko-KR').format(Math.round(num));
}

function formatPercent(num) {
    if (isNaN(num) || !isFinite(num)) return '0.0%';
    return (num * 100).toFixed(1) + '%';
}

// 날짜 범위 필터
function filterByDateRange(data, startDate, endDate) {
    return data.filter(row => {
        const date = row.base_time;
        return date >= startDate && date <= endDate;
    });
}

// 총 매출 집계 (중복 제거)
function aggregateTotal(data) {
    // mitem_code + customer_code + base_time 기준으로 중복 제거
    const seen = new Set();
    let totalRevenue = 0;
    let totalNet = 0;
    const uniqueProducts = new Set();
    const uniqueMaterials = new Set();
    const uniqueCustomers = new Set();

    data.forEach(row => {
        const key = `${row.mitem_code}_${row.customer_code}_${row.base_time}`;
        if (!seen.has(key)) {
            seen.add(key);
            totalRevenue += row.product_sales_revenue;
            totalNet += row.net_revenue;
        }
        uniqueProducts.add(row.mitem_code);
        uniqueMaterials.add(row.raw_cd);
        uniqueCustomers.add(row.customer_code);
    });

    return [{
        product_sales_revenue_sum: totalRevenue,
        net_revenue_sum: totalNet,
        net_margin: totalNet / totalRevenue,
        mitem_code_uniq: uniqueProducts.size,
        raw_cd_uniq: uniqueMaterials.size,
        customer_code_uniq: uniqueCustomers.size
    }];
}

// 월별 집계 (중복 제거)
function aggregateByMonth(data) {
    const grouped = {};
    const seen = {};

    data.forEach(row => {
        const month = row.base_time.substring(0, 7);
        const key = `${row.mitem_code}_${row.customer_code}_${row.base_time}`;

        if (!seen[month]) seen[month] = new Set();
        if (!grouped[month]) {
            grouped[month] = { product_sales_revenue_sum: 0, net_revenue_sum: 0 };
        }

        if (!seen[month].has(key)) {
            seen[month].add(key);
            grouped[month].product_sales_revenue_sum += row.product_sales_revenue;
            grouped[month].net_revenue_sum += row.net_revenue;
        }
    });

    return Object.entries(grouped)
        .map(([month, vals]) => ({
            month,
            ...vals,
            net_margin: vals.net_revenue_sum / vals.product_sales_revenue_sum
        }))
        .sort((a, b) => a.month.localeCompare(b.month));
}

// 분기별 집계 (중복 제거)
function aggregateByQuarter(data) {
    const grouped = {};
    const seen = {};

    data.forEach(row => {
        const date = new Date(row.base_time);
        const year = date.getFullYear();
        const quarter = Math.ceil((date.getMonth() + 1) / 3);
        const qKey = `${year}Q${quarter}`;
        const key = `${row.mitem_code}_${row.customer_code}_${row.base_time}`;

        if (!seen[qKey]) seen[qKey] = new Set();
        if (!grouped[qKey]) {
            grouped[qKey] = { product_sales_revenue_sum: 0, net_revenue_sum: 0 };
        }

        if (!seen[qKey].has(key)) {
            seen[qKey].add(key);
            grouped[qKey].product_sales_revenue_sum += row.product_sales_revenue;
            grouped[qKey].net_revenue_sum += row.net_revenue;
        }
    });

    return Object.entries(grouped)
        .map(([quarter, vals]) => ({
            quarter,
            ...vals,
            net_margin: vals.net_revenue_sum / vals.product_sales_revenue_sum
        }))
        .sort((a, b) => a.quarter.localeCompare(b.quarter));
}

// 반기별 집계 (중복 제거)
function aggregateByHalf(data) {
    const grouped = {};
    const seen = {};

    data.forEach(row => {
        const date = new Date(row.base_time);
        const year = date.getFullYear();
        const half = date.getMonth() < 6 ? 'H1' : 'H2';
        const hKey = `${year}${half}`;
        const key = `${row.mitem_code}_${row.customer_code}_${row.base_time}`;

        if (!seen[hKey]) seen[hKey] = new Set();
        if (!grouped[hKey]) {
            grouped[hKey] = { product_sales_revenue_sum: 0, net_revenue_sum: 0 };
        }

        if (!seen[hKey].has(key)) {
            seen[hKey].add(key);
            grouped[hKey].product_sales_revenue_sum += row.product_sales_revenue;
            grouped[hKey].net_revenue_sum += row.net_revenue;
        }
    });

    return Object.entries(grouped)
        .map(([half, vals]) => ({
            half,
            ...vals,
            net_margin: vals.net_revenue_sum / vals.product_sales_revenue_sum
        }))
        .sort((a, b) => a.half.localeCompare(b.half));
}

// 소재별 집계 (중복 허용 - 소재 기여도 파악용)
function aggregateByMaterial(data) {
    const grouped = {};

    data.forEach(row => {
        const key = row.raw_cd;
        if (!grouped[key]) {
            grouped[key] = {
                raw_cd: row.raw_cd,
                raw_nm: row.raw_nm,
                product_sales_revenue_sum: 0,
                net_revenue_sum: 0,
                products: new Set()
            };
        }
        grouped[key].product_sales_revenue_sum += row.product_sales_revenue;
        grouped[key].net_revenue_sum += row.net_revenue;
        grouped[key].products.add(row.mitem_code);
    });

    // 총 매출 계산 (중복 제거된)
    const totalStats = aggregateTotal(data)[0];
    const dedupTotal = totalStats.product_sales_revenue_sum;

    return Object.values(grouped)
        .map(vals => ({
            raw_cd: vals.raw_cd,
            raw_nm: vals.raw_nm,
            product_sales_revenue_sum: vals.product_sales_revenue_sum,
            net_revenue_sum: vals.net_revenue_sum,
            net_margin: vals.net_revenue_sum / vals.product_sales_revenue_sum,
            revenue_share: vals.product_sales_revenue_sum / dedupTotal,
            product_unique_cnt: vals.products.size
        }))
        .sort((a, b) => b.product_sales_revenue_sum - a.product_sales_revenue_sum);
}

// 제품라인별 집계 (중복 제거)
function aggregateByProductLine(data) {
    const grouped = {};
    const seen = {};

    data.forEach(row => {
        const pKey = `${row.product_name}_${row.customer_code}`;
        const key = `${row.mitem_code}_${row.customer_code}_${row.base_time}`;

        if (!seen[pKey]) seen[pKey] = new Set();
        if (!grouped[pKey]) {
            grouped[pKey] = {
                product_name: row.product_name,
                customer_name: row.customer_name,
                customer_code: row.customer_code,
                product_sales_revenue_sum: 0,
                net_revenue_sum: 0,
                items: new Set()
            };
        }

        if (!seen[pKey].has(key)) {
            seen[pKey].add(key);
            grouped[pKey].product_sales_revenue_sum += row.product_sales_revenue;
            grouped[pKey].net_revenue_sum += row.net_revenue;
        }
        grouped[pKey].items.add(row.mitem_code);
    });

    const totalStats = aggregateTotal(data)[0];
    const dedupTotal = totalStats.product_sales_revenue_sum;

    return Object.values(grouped)
        .map(vals => ({
            product_name: vals.product_name,
            customer_name: vals.customer_name,
            product_sales_revenue_sum: vals.product_sales_revenue_sum,
            net_revenue_sum: vals.net_revenue_sum,
            net_margin: vals.net_revenue_sum / vals.product_sales_revenue_sum,
            revenue_share: vals.product_sales_revenue_sum / dedupTotal,
            item_count: vals.items.size
        }))
        .sort((a, b) => b.product_sales_revenue_sum - a.product_sales_revenue_sum);
}

// 고객별 집계 (중복 제거)
function aggregateByCustomer(data) {
    const grouped = {};
    const seen = {};

    data.forEach(row => {
        const cKey = row.customer_code;
        const key = `${row.mitem_code}_${row.customer_code}_${row.base_time}`;

        if (!seen[cKey]) seen[cKey] = new Set();
        if (!grouped[cKey]) {
            grouped[cKey] = {
                customer_code: row.customer_code,
                customer_name: row.customer_name,
                product_sales_revenue_sum: 0,
                net_revenue_sum: 0,
                products: new Set()
            };
        }

        if (!seen[cKey].has(key)) {
            seen[cKey].add(key);
            grouped[cKey].product_sales_revenue_sum += row.product_sales_revenue;
            grouped[cKey].net_revenue_sum += row.net_revenue;
        }
        grouped[cKey].products.add(row.mitem_code);
    });

    const totalStats = aggregateTotal(data)[0];
    const dedupTotal = totalStats.product_sales_revenue_sum;

    return Object.values(grouped)
        .map(vals => ({
            customer_code: vals.customer_code,
            customer_name: vals.customer_name,
            product_sales_revenue_sum: vals.product_sales_revenue_sum,
            net_revenue_sum: vals.net_revenue_sum,
            net_margin: vals.net_revenue_sum / vals.product_sales_revenue_sum,
            revenue_share: vals.product_sales_revenue_sum / dedupTotal,
            product_unique_cnt: vals.products.size
        }))
        .sort((a, b) => b.product_sales_revenue_sum - a.product_sales_revenue_sum);
}

// 제형별 집계 (중복 제거)
function aggregateByFormulation(data) {
    const grouped = {};
    const seen = {};

    data.forEach(row => {
        const fKey = row.forml_code;
        const key = `${row.mitem_code}_${row.customer_code}_${row.base_time}`;

        if (!seen[fKey]) seen[fKey] = new Set();
        if (!grouped[fKey]) {
            grouped[fKey] = {
                forml_code: row.forml_code,
                forml_name: row.forml_name,
                product_sales_revenue_sum: 0,
                net_revenue_sum: 0,
                products: new Set()
            };
        }

        if (!seen[fKey].has(key)) {
            seen[fKey].add(key);
            grouped[fKey].product_sales_revenue_sum += row.product_sales_revenue;
            grouped[fKey].net_revenue_sum += row.net_revenue;
        }
        grouped[fKey].products.add(row.mitem_code);
    });

    const totalStats = aggregateTotal(data)[0];
    const dedupTotal = totalStats.product_sales_revenue_sum;

    return Object.values(grouped)
        .map(vals => ({
            forml_code: vals.forml_code,
            forml_name: vals.forml_name,
            product_sales_revenue_sum: vals.product_sales_revenue_sum,
            net_revenue_sum: vals.net_revenue_sum,
            net_margin: vals.net_revenue_sum / vals.product_sales_revenue_sum,
            revenue_share: vals.product_sales_revenue_sum / dedupTotal,
            product_unique_cnt: vals.products.size
        }))
        .sort((a, b) => b.product_sales_revenue_sum - a.product_sales_revenue_sum);
}

// 기본값: 로컬 샘플 fallback 사용 (API 미설정)
// 실데이터 테스트 시 baseUrl을 채우거나 localStorage.BTI_API_BASE_URL을 사용하세요.
window.BTI_API_CONFIG = window.BTI_API_CONFIG || {
    baseUrl: 'https://su6yx51c2a.execute-api.ap-northeast-2.amazonaws.com/prd/bti_revenue'
};

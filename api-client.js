(function (window) {
    const runtimeConfig = window.BTI_API_CONFIG || {};
    const storageBaseUrl = (() => {
        try {
            return window.localStorage.getItem('BTI_API_BASE_URL') || '';
        } catch (_error) {
            return '';
        }
    })();
    const baseUrl = String(runtimeConfig.baseUrl || storageBaseUrl || '').replace(/\/$/, '');
    const defaultHeaders = runtimeConfig.headers || {};

    function buildUrl(path, params) {
        const url = new URL((baseUrl || '') + path, window.location.origin);
        if (params) {
            Object.entries(params).forEach(([key, value]) => {
                if (value !== undefined && value !== null && value !== '') {
                    url.searchParams.set(key, String(value));
                }
            });
        }
        return url.toString();
    }

    async function getJson(path, params) {
        if (!baseUrl) {
            throw new Error('API base URL이 설정되지 않았습니다. window.BTI_API_CONFIG.baseUrl을 지정하세요.');
        }

        const response = await fetch(buildUrl(path, params), {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                ...defaultHeaders
            }
        });

        let payload = null;
        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
            payload = await response.json();
        } else {
            const text = await response.text();
            payload = { message: text };
        }

        if (!response.ok) {
            const message = payload?.message || `API 요청 실패 (${response.status})`;
            throw new Error(message);
        }

        return payload;
    }

    window.BTIApiClient = {
        isConfigured() {
            return Boolean(baseUrl);
        },
        getBaseUrl() {
            return baseUrl;
        },
        getReportData(params) {
            return getJson('/report-data', params);
        },
        getMaterials() {
            return getJson('/materials');
        },
        getDataStatus() {
            return getJson('/data-status');
        }
    };
})(window);

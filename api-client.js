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
    const authTokenStorageKey = 'BTI_AUTH_TOKEN';

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

    function getAuthToken() {
        try {
            return window.localStorage.getItem(authTokenStorageKey) || '';
        } catch (_e) {
            return '';
        }
    }

    async function requestJson(method, path, { params, body, auth = false } = {}) {
        if (!baseUrl) {
            throw new Error('API base URL이 설정되지 않았습니다. window.BTI_API_CONFIG.baseUrl을 지정하세요.');
        }

        const headers = {
            'Accept': 'application/json',
            ...defaultHeaders
        };
        if (body !== undefined) {
            headers['Content-Type'] = 'application/json';
        }
        if (auth) {
            const token = getAuthToken();
            if (!token) {
                throw new Error('로그인이 필요합니다.');
            }
            headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch(buildUrl(path, params), {
            method,
            headers,
            body: body !== undefined ? JSON.stringify(body) : undefined
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
            if (
                path === '/materials/requests' &&
                typeof message === 'string' &&
                message.includes('현재 소재 추가/수정/삭제 신청 기능은 점검 중입니다.')
            ) {
                try {
                    window.alert(message);
                } catch (_e) {
                    // no-op
                }
                try {
                    window.dispatchEvent(new CustomEvent('bti:material-request-blocked', { detail: { message } }));
                } catch (_e) {
                    // no-op
                }
            }
            throw new Error(message);
        }

        return payload;
    }

    function getJson(path, params) {
        return requestJson('GET', path, { params });
    }

    window.BTIApiClient = {
        isConfigured() {
            return Boolean(baseUrl);
        },
        getBaseUrl() {
            return baseUrl;
        },
        getReportData(params) {
            return requestJson('GET', '/report-data', { params, auth: true });
        },
        getMaterials() {
            return requestJson('GET', '/materials', { auth: true });
        },
        getDataStatus() {
            return requestJson('GET', '/data-status', { auth: true });
        },
        authLogin(payload) {
            return requestJson('POST', '/auth/login', { body: payload });
        },
        authChangePassword(payload) {
            return requestJson('POST', '/auth/change-password', { body: payload, auth: true });
        },
        getAdminAccounts() {
            return requestJson('GET', '/admin/accounts', { auth: true });
        },
        getAdminTeams() {
            return requestJson('GET', '/admin/teams', { auth: true });
        },
        createAdminTeam(payload) {
            return requestJson('POST', '/admin/teams', { body: payload, auth: true });
        },
        updateAdminTeam(teamId, payload) {
            return requestJson('PATCH', `/admin/teams/${encodeURIComponent(teamId)}`, { body: payload, auth: true });
        },
        deactivateAdminTeam(teamId) {
            return requestJson('POST', `/admin/teams/${encodeURIComponent(teamId)}/deactivate`, { auth: true });
        },
        deleteAdminTeam(teamId) {
            return requestJson('DELETE', `/admin/teams/${encodeURIComponent(teamId)}`, { auth: true });
        },
        createAdminAccount(payload) {
            return requestJson('POST', '/admin/accounts', { body: payload, auth: true });
        },
        deleteAdminAccount(accountId) {
            return requestJson('DELETE', `/admin/accounts/${encodeURIComponent(accountId)}`, { auth: true });
        },
        resetAdminAccountPassword(accountId) {
            return requestJson('POST', `/admin/accounts/${encodeURIComponent(accountId)}/reset-password`, { auth: true });
        },
        getMaterialRequests() {
            return requestJson('GET', '/materials/requests', { auth: true });
        },
        createMaterialRequest(payload) {
            return requestJson('POST', '/materials/requests', { body: payload, auth: true });
        },
        approveMaterialRequest(requestId) {
            return requestJson('POST', `/materials/requests/${encodeURIComponent(requestId)}/approve`, { auth: true });
        },
        rejectMaterialRequest(requestId) {
            return requestJson('POST', `/materials/requests/${encodeURIComponent(requestId)}/reject`, { auth: true });
        }
    };
})(window);

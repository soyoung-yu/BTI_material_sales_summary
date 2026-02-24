(function () {
    const MATERIALS_STORE_KEY = 'BTI_MATERIALS_STORE_V1';
    const useApi = () => Boolean(window.BTIApiClient?.isConfigured());

    function read() {
        try {
            const raw = localStorage.getItem(MATERIALS_STORE_KEY);
            return raw ? JSON.parse(raw) : null;
        } catch (_e) {
            return null;
        }
    }

    function write(rows) {
        localStorage.setItem(MATERIALS_STORE_KEY, JSON.stringify(rows));
    }

    function nowIso() {
        return new Date().toISOString();
    }

    function todayYmd() {
        return new Date().toISOString().slice(0, 10);
    }

    function ensureId(row) {
        return row._id ? row : { ...row, _id: `mat-${Date.now()}-${Math.random().toString(36).slice(2, 8)}` };
    }

    function seed(initialRows) {
        const existing = read();
        if (Array.isArray(existing) && existing.length > 0) return existing;
        const rows = (initialRows || []).map(row => ensureId({
            mmsta: row.mmsta ?? '',
            researcher: row.researcher ?? '',
            created: row.created ?? todayYmd(),
            approval_status: row.approval_status ?? '완료',
            request_type: row.request_type ?? 'NONE',
            request_status: row.request_status ?? (row.approval_status === '완료' ? 'APPROVED' : 'PENDING'),
            requested_by: row.requested_by ?? '',
            requested_by_team_id: row.requested_by_team_id ?? '',
            requested_at: row.requested_at ?? '',
            approved_by: row.approved_by ?? '',
            approved_at: row.approved_at ?? '',
            ...row
        }));
        write(rows);
        return rows;
    }

    function getAll() {
        const rows = read() || [];
        if (!rows.every(r => r && r._id)) {
            const upgraded = rows.map(ensureId);
            write(upgraded);
            return upgraded;
        }
        return rows;
    }

    function setAll(rows) {
        write(rows.map(ensureId));
    }

    async function createRequest(payload, user) {
        if (useApi()) {
            const requestType = String(payload.request_type || payload.requestType || 'CREATE').toUpperCase();
            return window.BTIApiClient.createMaterialRequest({
                request_type: requestType,
                payload: {
                    raw_cd: payload.raw_cd,
                    raw_nm: payload.raw_nm,
                    mmsta: payload.mmsta ?? '',
                    researcher: payload.researcher || user?.name || '',
                    created: payload.created || todayYmd(),
                    approval_status: payload.approval_status || ''
                }
            });
        }
        const rows = getAll();
        rows.unshift(ensureId({
            raw_cd: payload.raw_cd,
            raw_nm: payload.raw_nm,
            mmsta: payload.mmsta ?? '',
            researcher: payload.researcher || user?.name || '',
            created: todayYmd(),
            approval_status: '등록중',
            request_type: 'CREATE',
            request_status: 'PENDING',
            requested_by: user?.name || '',
            requested_by_team_id: user?.team_id || '',
            requested_at: nowIso(),
            approved_by: '',
            approved_at: ''
        }));
        write(rows);
        return rows;
    }

    async function updateRequest(rowId, patch, user) {
        if (useApi()) {
            return window.BTIApiClient.createMaterialRequest({
                request_type: 'UPDATE',
                payload: {
                    raw_cd: patch.raw_cd,
                    raw_nm: patch.raw_nm,
                    mmsta: patch.mmsta ?? '',
                    researcher: patch.researcher || user?.name || '',
                    created: patch.created || todayYmd()
                }
            });
        }
        const rows = getAll();
        const idx = rows.findIndex(r => r._id === rowId);
        if (idx < 0) throw new Error('대상 소재를 찾을 수 없습니다.');
        rows[idx] = {
            ...rows[idx],
            ...patch,
            approval_status: '수정중',
            request_type: 'UPDATE',
            request_status: 'PENDING',
            requested_by: user?.name || '',
            requested_by_team_id: user?.team_id || '',
            requested_at: nowIso()
        };
        write(rows);
        return rows;
    }

    async function requestDelete(rowId, user, rowData) {
        if (useApi()) {
            return window.BTIApiClient.createMaterialRequest({
                request_type: 'DELETE',
                payload: {
                    raw_cd: rowData?.raw_cd || '',
                    raw_nm: rowData?.raw_nm || ''
                }
            });
        }
        const rows = getAll();
        const idx = rows.findIndex(r => r._id === rowId);
        if (idx < 0) throw new Error('대상 소재를 찾을 수 없습니다.');
        const row = rows[idx];
        if (row.approval_status !== '완료') {
            rows.splice(idx, 1);
            write(rows);
            return { rows, removedPending: true };
        }
        rows[idx] = {
            ...row,
            approval_status: '삭제중',
            request_type: 'DELETE',
            request_status: 'PENDING',
            requested_by: user?.name || '',
            requested_by_team_id: user?.team_id || '',
            requested_at: nowIso()
        };
        write(rows);
        return { rows, removedPending: false };
    }

    async function getPendingRequests(user) {
        if (useApi()) {
            const result = await window.BTIApiClient.getMaterialRequests();
            const rows = Array.isArray(result?.rows) ? result.rows : [];
            return rows
                .filter(r => String(r?.request_status || '') === 'PENDING')
                .map(r => ({
                    ...r,
                    _id: r.request_id,
                    raw_cd: r?.payload?.raw_cd || '',
                    raw_nm: r?.payload?.raw_nm || '',
                    requested_by: r.requested_by_name || '',
                    requested_by_team_id: r.team_id || '',
                    requested_at: r.created_at || ''
                }));
        }
        const rows = getAll().filter(r => r.request_status === 'PENDING');
        if (!user) return [];
        if (user.role === 'ADMIN') return rows;
        if (user.role === 'TEAM_ADMIN') {
            return rows.filter(r => String(r.requested_by_team_id || '') === String(user.team_id || ''));
        }
        return [];
    }

    async function approveRequest(rowId, approver) {
        if (useApi()) {
            return window.BTIApiClient.approveMaterialRequest(rowId);
        }
        const rows = getAll();
        const idx = rows.findIndex(r => r._id === rowId);
        if (idx < 0) throw new Error('승인 대상 요청을 찾을 수 없습니다.');
        const row = rows[idx];
        if (row.request_status !== 'PENDING') throw new Error('이미 처리된 요청입니다.');
        if (approver?.role === 'TEAM_ADMIN' && row.requested_by_team_id !== approver.team_id) {
            throw new Error('본인 팀 요청만 승인할 수 있습니다.');
        }

        if (row.request_type === 'DELETE') {
            rows.splice(idx, 1);
        } else {
            rows[idx] = {
                ...row,
                approval_status: '완료',
                request_type: 'NONE',
                request_status: 'APPROVED',
                approved_by: approver?.name || '',
                approved_at: nowIso()
            };
        }
        write(rows);
        return rows;
    }

    window.BTIMaterialsStore = {
        seed,
        getAll,
        setAll,
        createRequest,
        updateRequest,
        requestDelete,
        getPendingRequests,
        approveRequest
    };
})();

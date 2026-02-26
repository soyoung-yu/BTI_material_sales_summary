(function () {
    const ACCOUNTS_KEY = 'BTI_ACCOUNTS';
    const SESSION_KEY = 'BTI_SESSION';
    const AUTH_TOKEN_KEY = 'BTI_AUTH_TOKEN';
    const AUTH_USER_KEY = 'BTI_AUTH_USER';
    const TEAMS_KEY = 'BTI_TEAMS';
    const DEFAULT_RESET_PASSWORD = 'firstpassword';

    const ROLES = {
        ADMIN: 'ADMIN',
        TEAM_ADMIN: 'TEAM_ADMIN',
        TEAM_MEMBER: 'TEAM_MEMBER'
    };

    const DEFAULT_ACCOUNTS = [
        {
            account_id: 'acc-admin',
            login_id: 'admin',
            password: 'admin1234',
            name: '관리자',
            team_id: 'HQ',
            team_name: '관리자',
            role: ROLES.ADMIN,
            active: true
        },
        {
            account_id: 'acc-mb2-admin',
            login_id: 'mb2_admin',
            password: 'mb21234',
            name: 'MB2팀장',
            team_id: 'MB2',
            team_name: 'MB2팀',
            role: ROLES.TEAM_ADMIN,
            active: true
        },
        {
            account_id: 'acc-mb2-member',
            login_id: 'mb2_user',
            password: 'mb21234',
            name: 'MB2팀원',
            team_id: 'MB2',
            team_name: 'MB2팀',
            role: ROLES.TEAM_MEMBER,
            active: true
        }
    ];

    function readJson(key, fallback) {
        try {
            const raw = localStorage.getItem(key);
            return raw ? JSON.parse(raw) : fallback;
        } catch (_e) {
            return fallback;
        }
    }

    function writeJson(key, value) {
        localStorage.setItem(key, JSON.stringify(value));
    }

    function ensureAccounts() {
        const existing = readJson(ACCOUNTS_KEY, null);
        if (Array.isArray(existing) && existing.length > 0) return existing;
        writeJson(ACCOUNTS_KEY, DEFAULT_ACCOUNTS);
        return DEFAULT_ACCOUNTS.slice();
    }

    function deriveTeamsFromAccounts(accounts) {
        const rows = [];
        const seen = new Set();
        (accounts || []).forEach((a) => {
            const teamId = String(a.team_id || '').trim().toUpperCase();
            if (!teamId || seen.has(teamId)) return;
            rows.push({
                team_id: teamId,
                team_name: String(a.team_name || (teamId === 'HQ' ? '관리자' : `${teamId}팀`)).trim() || teamId,
                active: true,
                is_system: teamId === 'HQ'
            });
            seen.add(teamId);
        });
        if (!seen.has('HQ')) {
            rows.unshift({ team_id: 'HQ', team_name: '관리자', active: true, is_system: true });
        }
        if (!seen.has('MB2')) {
            rows.push({ team_id: 'MB2', team_name: 'MB2팀', active: true, is_system: false });
        }
        rows.sort((a, b) => (a.is_system ? -1 : 1) - (b.is_system ? -1 : 1) || a.team_id.localeCompare(b.team_id));
        return rows;
    }

    function getTeamsFallback() {
        const existing = readJson(TEAMS_KEY, null);
        if (Array.isArray(existing) && existing.length > 0) return existing;
        const derived = deriveTeamsFromAccounts(getAccounts());
        writeJson(TEAMS_KEY, derived);
        return derived;
    }

    function saveTeamsFallback(rows) {
        writeJson(TEAMS_KEY, rows);
    }

    function getAccounts() {
        return ensureAccounts();
    }

    function saveAccounts(accounts) {
        writeJson(ACCOUNTS_KEY, accounts);
    }

    function getCurrentUser() {
        if (window.BTIApiClient?.isConfigured()) {
            return readJson(AUTH_USER_KEY, null);
        }
        const session = readJson(SESSION_KEY, null);
        if (!session?.login_id) return null;
        const user = getAccounts().find(a => a.login_id === session.login_id && a.active !== false);
        return user || null;
    }

    async function login(loginId, password) {
        if (window.BTIApiClient?.isConfigured()) {
            const result = await window.BTIApiClient.authLogin({ login_id: loginId, password });
            const token = String(result?.token || '');
            const user = result?.user || null;
            if (!token || !user) throw new Error('로그인 응답이 올바르지 않습니다.');
            localStorage.setItem(AUTH_TOKEN_KEY, token);
            writeJson(AUTH_USER_KEY, user);
            window.dispatchEvent(new CustomEvent('bti-auth-changed'));
            return user;
        }
        const user = getAccounts().find(
            a => a.login_id === loginId && a.password === password && a.active !== false
        );
        if (!user) {
            throw new Error('아이디 또는 비밀번호가 올바르지 않습니다.');
        }
        writeJson(SESSION_KEY, { login_id: user.login_id, logged_in_at: new Date().toISOString() });
        window.dispatchEvent(new CustomEvent('bti-auth-changed'));
        return user;
    }

    function logout() {
        localStorage.removeItem(SESSION_KEY);
        localStorage.removeItem(AUTH_TOKEN_KEY);
        localStorage.removeItem(AUTH_USER_KEY);
        window.dispatchEvent(new CustomEvent('bti-auth-changed'));
    }

    async function createAccount(payload) {
        if (window.BTIApiClient?.isConfigured()) {
            const result = await window.BTIApiClient.createAdminAccount(payload);
            return result?.account || result;
        }
        const accounts = getAccounts();
        const loginId = String(payload.login_id || '').trim();
        if (!loginId) throw new Error('로그인 ID를 입력해주세요.');
        if (accounts.some(a => a.login_id === loginId)) throw new Error('이미 존재하는 로그인 ID입니다.');

        const role = payload.role;
        if (![ROLES.TEAM_ADMIN, ROLES.TEAM_MEMBER].includes(role)) {
            throw new Error('생성 가능한 권한은 팀 관리자/팀원입니다.');
        }

        const next = {
            account_id: `acc-${Date.now()}`,
            login_id: loginId,
            password: String(payload.password || ''),
            name: String(payload.name || '').trim(),
            team_id: String(payload.team_id || '').trim(),
            team_name: String(payload.team_name || '').trim() || String(payload.team_id || '').trim(),
            role,
            active: payload.active !== false
        };

        if (!next.password || !next.name || !next.team_id) {
            throw new Error('ID/비밀번호/이름/팀은 필수입니다.');
        }

        accounts.push(next);
        saveAccounts(accounts);
        return next;
    }

    async function deleteAccount(accountId) {
        if (window.BTIApiClient?.isConfigured()) {
            return window.BTIApiClient.deleteAdminAccount(accountId);
        }
        const accounts = getAccounts();
        const idx = accounts.findIndex(a => a.account_id === accountId);
        if (idx < 0) throw new Error('계정을 찾을 수 없습니다.');
        if (accounts[idx].role === ROLES.ADMIN) {
            throw new Error('관리자 계정은 삭제할 수 없습니다.');
        }
        const [deleted] = accounts.splice(idx, 1);
        saveAccounts(accounts);
        const session = readJson(SESSION_KEY, null);
        if (session?.login_id === deleted.login_id) {
            logout();
        }
        return deleted;
    }

    async function resetPassword(accountId, newPassword) {
        if (window.BTIApiClient?.isConfigured()) {
            return window.BTIApiClient.resetAdminAccountPassword(accountId);
        }
        const accounts = getAccounts();
        const idx = accounts.findIndex(a => a.account_id === accountId);
        if (idx < 0) throw new Error('계정을 찾을 수 없습니다.');
        if (accounts[idx].role === ROLES.ADMIN) {
            throw new Error('관리자 계정 비밀번호 초기화는 여기서 지원하지 않습니다.');
        }
        accounts[idx] = {
            ...accounts[idx],
            password: String(newPassword || DEFAULT_RESET_PASSWORD)
        };
        saveAccounts(accounts);
        return accounts[idx];
    }

    async function changeOwnPassword(currentPassword, newPassword) {
        if (window.BTIApiClient?.isConfigured()) {
            return window.BTIApiClient.authChangePassword({
                current_password: currentPassword,
                new_password: newPassword
            });
        }
        const user = getCurrentUser();
        if (!user) throw new Error('로그인이 필요합니다.');
        if (!currentPassword || !newPassword) throw new Error('현재 비밀번호와 새 비밀번호를 입력해주세요.');
        if (String(user.password) !== String(currentPassword)) {
            throw new Error('현재 비밀번호가 올바르지 않습니다.');
        }
        if (String(newPassword).length < 4) {
            throw new Error('새 비밀번호는 4자 이상이어야 합니다.');
        }

        const accounts = getAccounts();
        const idx = accounts.findIndex(a => a.account_id === user.account_id);
        if (idx < 0) throw new Error('계정을 찾을 수 없습니다.');
        accounts[idx] = { ...accounts[idx], password: String(newPassword) };
        saveAccounts(accounts);
        return accounts[idx];
    }

    async function listAccounts() {
        if (window.BTIApiClient?.isConfigured()) {
            const result = await window.BTIApiClient.getAdminAccounts();
            return Array.isArray(result?.rows) ? result.rows : [];
        }
        return getAccounts();
    }

    async function listTeams(options = {}) {
        const includeInactive = Boolean(options.includeInactive);
        if (window.BTIApiClient?.isConfigured()) {
            const result = await window.BTIApiClient.getAdminTeams();
            let rows = Array.isArray(result?.rows) ? result.rows : [];
            if (!includeInactive) rows = rows.filter(t => t.active !== false);
            return rows;
        }
        let rows = getTeamsFallback();
        if (!includeInactive) rows = rows.filter(t => t.active !== false);
        return rows;
    }

    async function createTeam(payload) {
        const teamId = String(payload?.team_id || payload?.teamId || '').trim().toUpperCase();
        const teamName = String(payload?.team_name || payload?.teamName || '').trim();
        if (!teamId || !teamName) throw new Error('팀 ID와 팀명을 입력해주세요.');

        if (window.BTIApiClient?.isConfigured()) {
            const result = await window.BTIApiClient.createAdminTeam({ team_id: teamId, team_name: teamName });
            return result?.team || result;
        }

        const rows = getTeamsFallback();
        if (rows.some(t => String(t.team_id).toUpperCase() === teamId)) {
            throw new Error('이미 존재하는 팀 ID입니다.');
        }
        const next = [...rows, { team_id: teamId, team_name: teamName, active: true, is_system: false }];
        saveTeamsFallback(next);
        return next[next.length - 1];
    }

    async function updateTeam(teamId, payload) {
        const normalizedTeamId = String(teamId || '').trim().toUpperCase();
        const teamName = String(payload?.team_name || payload?.teamName || '').trim();
        if (!normalizedTeamId || !teamName) throw new Error('팀 정보가 올바르지 않습니다.');

        if (window.BTIApiClient?.isConfigured()) {
            const result = await window.BTIApiClient.updateAdminTeam(normalizedTeamId, { team_name: teamName });
            return result?.team || result;
        }

        const rows = getTeamsFallback();
        const idx = rows.findIndex(t => String(t.team_id).toUpperCase() === normalizedTeamId);
        if (idx < 0) throw new Error('팀을 찾을 수 없습니다.');
        if (rows[idx].is_system || normalizedTeamId === 'HQ') throw new Error('시스템 팀은 수정할 수 없습니다.');
        rows[idx] = { ...rows[idx], team_name: teamName };
        saveTeamsFallback(rows);
        return rows[idx];
    }

    async function deactivateTeam(teamId) {
        const normalizedTeamId = String(teamId || '').trim().toUpperCase();
        if (!normalizedTeamId) throw new Error('팀 정보가 올바르지 않습니다.');

        if (window.BTIApiClient?.isConfigured()) {
            const result = await window.BTIApiClient.deactivateAdminTeam(normalizedTeamId);
            return result?.team || result;
        }

        const rows = getTeamsFallback();
        const idx = rows.findIndex(t => String(t.team_id).toUpperCase() === normalizedTeamId);
        if (idx < 0) throw new Error('팀을 찾을 수 없습니다.');
        if (rows[idx].is_system || normalizedTeamId === 'HQ') throw new Error('시스템 팀은 비활성화할 수 없습니다.');
        const accounts = getAccounts();
        if (accounts.some(a => String(a.team_id).toUpperCase() === normalizedTeamId && a.active !== false)) {
            throw new Error('활성 계정이 존재하는 팀은 비활성화할 수 없습니다.');
        }
        rows[idx] = { ...rows[idx], active: false };
        saveTeamsFallback(rows);
        return rows[idx];
    }

    async function deleteTeam(teamId) {
        const normalizedTeamId = String(teamId || '').trim().toUpperCase();
        if (!normalizedTeamId) throw new Error('팀 정보가 올바르지 않습니다.');

        if (window.BTIApiClient?.isConfigured()) {
            return window.BTIApiClient.deleteAdminTeam(normalizedTeamId);
        }

        if (normalizedTeamId === 'HQ') throw new Error('시스템 팀은 삭제할 수 없습니다.');

        const rows = getTeamsFallback();
        const idx = rows.findIndex(t => String(t.team_id).toUpperCase() === normalizedTeamId);
        if (idx < 0) throw new Error('팀을 찾을 수 없습니다.');
        if (rows[idx].is_system) throw new Error('시스템 팀은 삭제할 수 없습니다.');

        const accounts = getAccounts();
        const remainingAccounts = accounts.filter(a => String(a.team_id || '').trim().toUpperCase() !== normalizedTeamId);
        const deletedAccounts = accounts.filter(a => String(a.team_id || '').trim().toUpperCase() === normalizedTeamId);
        saveAccounts(remainingAccounts);

        rows.splice(idx, 1);
        saveTeamsFallback(rows);
        return { deletedAccountCount: deletedAccounts.length };
    }

    function canAccessPage(page, user) {
        if (page === 'index') return true;
        if (page === 'materials') return Boolean(user);
        if (page === 'approvals') return Boolean(user && [ROLES.TEAM_ADMIN, ROLES.ADMIN].includes(user.role));
        if (page === 'admin') return Boolean(user && user.role === ROLES.ADMIN);
        return true;
    }

    function buildNavItems(user, currentPage) {
        const items = [{ key: 'index', href: 'index.html', label: '리포트 생성' }];
        if (user) items.push({ key: 'materials', href: 'materials.html', label: '소재 관리' });
        if (user && [ROLES.TEAM_ADMIN, ROLES.ADMIN].includes(user.role)) {
            items.push({ key: 'approvals', href: 'approvals.html', label: '승인 요청' });
        }
        if (user && user.role === ROLES.ADMIN) {
            items.push({ key: 'admin', href: 'admin.html', label: '관리자' });
        }
        return items.map(item => (
            `<li><a href="${item.href}" class="${item.key === currentPage ? 'active' : ''}">${item.label}</a></li>`
        )).join('');
    }

    function ensureLoginModal() {
        if (document.getElementById('authModal') && document.getElementById('pwChangeModal')) return;
        const style = document.createElement('style');
        style.textContent = `
            .auth-btn{border:1px solid #cbd5e1;background:#fff;color:#1e293b;padding:6px 10px;border-radius:6px;cursor:pointer;font-size:13px}
            .auth-btn.primary{background:#1a365d;color:#fff;border-color:#1a365d}
            .auth-modal-overlay{position:fixed;inset:0;background:rgba(15,23,42,.45);display:none;align-items:center;justify-content:center;z-index:9999}
            .auth-modal-overlay.active{display:flex}
            .auth-modal{width:min(420px,92vw);background:#fff;border-radius:12px;padding:20px;box-shadow:0 12px 32px rgba(0,0,0,.18)}
            .auth-modal-header{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:12px}
            .auth-modal h3{margin:0;font-size:18px;color:#0f172a}
            .auth-modal-close{border:1px solid #cbd5e1;background:#fff;color:#475569;border-radius:8px;width:32px;height:32px;display:inline-flex;align-items:center;justify-content:center;cursor:pointer;font-size:18px;line-height:1}
            .auth-field{display:flex;flex-direction:column;gap:6px;margin-bottom:12px}
            .auth-field input{padding:10px 12px;border:1px solid #cbd5e1;border-radius:8px;font-size:14px}
            .auth-modal-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:8px}
            .auth-error{color:#dc2626;font-size:13px;min-height:18px}
        `;
        document.head.appendChild(style);

        const modal = document.createElement('div');
        modal.id = 'authModal';
        modal.className = 'auth-modal-overlay';
        modal.innerHTML = `
            <div class="auth-modal">
                <div class="auth-modal-header">
                    <h3>로그인</h3>
                    <button type="button" class="auth-modal-close" id="authCloseBtn" aria-label="로그인 팝업 닫기">×</button>
                </div>
                <div class="auth-field">
                    <label for="authLoginId">아이디</label>
                    <input id="authLoginId" type="text" autocomplete="username">
                </div>
                <div class="auth-field">
                    <label for="authPassword">비밀번호</label>
                    <input id="authPassword" type="password" autocomplete="current-password">
                </div>
                <div id="authError" class="auth-error"></div>
                <div class="auth-modal-actions">
                    <button type="button" class="auth-btn" id="authCancelBtn">취소</button>
                    <button type="button" class="auth-btn primary" id="authSubmitBtn">로그인</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);

        attachBackdropGuard(modal, 'active');
        document.getElementById('authCancelBtn').addEventListener('click', closeLoginModal);
        document.getElementById('authCloseBtn').addEventListener('click', closeLoginModal);
        document.getElementById('authSubmitBtn').addEventListener('click', submitLogin);
        document.getElementById('authPassword').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') submitLogin();
        });

        const pwModal = document.createElement('div');
        pwModal.id = 'pwChangeModal';
        pwModal.className = 'auth-modal-overlay';
        pwModal.innerHTML = `
            <div class="auth-modal">
                <div class="auth-modal-header">
                    <h3>비밀번호 변경</h3>
                    <button type="button" class="auth-modal-close" id="pwCloseBtn" aria-label="비밀번호 변경 팝업 닫기">×</button>
                </div>
                <div class="auth-field">
                    <label for="pwCurrent">현재 비밀번호</label>
                    <input id="pwCurrent" type="password" autocomplete="current-password">
                </div>
                <div class="auth-field">
                    <label for="pwNext">새 비밀번호</label>
                    <input id="pwNext" type="password" autocomplete="new-password">
                </div>
                <div id="pwChangeError" class="auth-error"></div>
                <div class="auth-modal-actions">
                    <button type="button" class="auth-btn" id="pwCancelBtn">취소</button>
                    <button type="button" class="auth-btn primary" id="pwSubmitBtn">변경</button>
                </div>
            </div>
        `;
        document.body.appendChild(pwModal);
        attachBackdropGuard(pwModal, 'active');
        document.getElementById('pwCancelBtn').addEventListener('click', closePasswordModal);
        document.getElementById('pwCloseBtn').addEventListener('click', closePasswordModal);
        document.getElementById('pwSubmitBtn').addEventListener('click', submitPasswordChange);
        document.getElementById('pwNext').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') submitPasswordChange();
        });
    }

    function attachBackdropGuard(overlayEl, activeClassName) {
        if (!overlayEl) return;

        ['mousedown', 'mouseup', 'click'].forEach(evtName => {
            overlayEl.addEventListener(evtName, (e) => {
                if (e.target !== overlayEl) return;
                e.preventDefault();
                e.stopPropagation();
                if (typeof e.stopImmediatePropagation === 'function') e.stopImmediatePropagation();
            }, true);
        });

        // Some previously attached listeners (or stale cached handlers) may still remove the class.
        // Re-assert the open state on backdrop click so the modal stays open consistently.
        overlayEl.addEventListener('click', (e) => {
            if (e.target !== overlayEl) return;
            setTimeout(() => {
                if (overlayEl.isConnected) overlayEl.classList.add(activeClassName);
            }, 0);
        });
    }

    function openLoginModal() {
        ensureLoginModal();
        document.getElementById('authError').textContent = '';
        document.getElementById('authLoginId').value = '';
        document.getElementById('authPassword').value = '';
        document.getElementById('authModal').classList.add('active');
        document.getElementById('authLoginId').focus();
    }

    function closeLoginModal() {
        const modal = document.getElementById('authModal');
        if (modal) modal.classList.remove('active');
    }

    function openPasswordModal() {
        ensureLoginModal();
        document.getElementById('pwChangeError').textContent = '';
        document.getElementById('pwCurrent').value = '';
        document.getElementById('pwNext').value = '';
        document.getElementById('pwChangeModal').classList.add('active');
        document.getElementById('pwCurrent').focus();
    }

    function closePasswordModal() {
        const modal = document.getElementById('pwChangeModal');
        if (modal) modal.classList.remove('active');
    }

    async function submitLogin() {
        const loginId = document.getElementById('authLoginId').value.trim();
        const password = document.getElementById('authPassword').value;
        try {
            await login(loginId, password);
            closeLoginModal();
            location.reload();
        } catch (err) {
            document.getElementById('authError').textContent = err.message || '로그인에 실패했습니다.';
        }
    }

    async function submitPasswordChange() {
        const currentPassword = document.getElementById('pwCurrent').value;
        const newPassword = document.getElementById('pwNext').value;
        try {
            await changeOwnPassword(currentPassword, newPassword);
            closePasswordModal();
            alert('비밀번호가 변경되었습니다.');
        } catch (err) {
            document.getElementById('pwChangeError').textContent = err.message || '비밀번호 변경에 실패했습니다.';
        }
    }

    function renderHeaderUser(user) {
        const container = document.querySelector('.user-info');
        if (!container) return;
        if (!user) {
            container.innerHTML = `<button type="button" class="auth-btn primary" id="loginBtn">로그인</button>`;
            container.querySelector('#loginBtn').addEventListener('click', openLoginModal);
            return;
        }
        container.innerHTML = `
            <span class="team-badge">${user.team_name || user.team_id}</span>
            <span>${user.name}</span>
            <button type="button" class="auth-btn" id="changePwBtn">비밀번호 변경</button>
            <button type="button" class="auth-btn" id="logoutBtn">로그아웃</button>
        `;
        container.querySelector('#changePwBtn').addEventListener('click', openPasswordModal);
        container.querySelector('#logoutBtn').addEventListener('click', () => {
            logout();
            location.reload();
        });
    }

    function renderNav(user, currentPage) {
        const navList = document.querySelector('.nav ul');
        if (!navList) return;
        navList.innerHTML = buildNavItems(user, currentPage);
    }

    function bootstrap(options) {
        ensureAccounts();
        ensureLoginModal();
        const user = getCurrentUser();
        renderHeaderUser(user);
        renderNav(user, options?.page || '');

        if (!canAccessPage(options?.page, user)) {
            alert('접근 권한이 없습니다.');
            location.href = 'index.html';
            return { user: null, denied: true };
        }
        return { user, denied: false };
    }

    function requireAuthenticated() {
        const user = getCurrentUser();
        if (!user) throw new Error('로그인이 필요합니다.');
        return user;
    }

    window.BTIAuth = {
        ROLES,
        DEFAULT_RESET_PASSWORD,
        getAccounts,
        listAccounts,
        listTeams,
        getCurrentUser,
        login,
        logout,
        createTeam,
        updateTeam,
        deactivateTeam,
        deleteTeam,
        createAccount,
        deleteAccount,
        resetPassword,
        changeOwnPassword,
        bootstrap,
        requireAuthenticated,
        openLoginModal,
        openPasswordModal,
        canAccessPage
    };
})();

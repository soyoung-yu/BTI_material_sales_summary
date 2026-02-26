# BTI 소재 기반 매출 요약 사이트 기능명세서 (현재 구현 기준)

## 1. 한눈에 보기

### 1.1 사이트 목적
- 기간 기반 매출 데이터를 조회하고, 요약 리포트를 미리보기/엑셀로 다운로드한다.
- 팀 소재 목록을 조회하고 소재 추가/수정/삭제 요청을 등록한다.
- 요청자는 `내 요청 내역`에서 상태(`신청/완료/반려`)를 확인한다.
- 팀 관리자/관리자는 승인 요청을 `승인/반려` 처리한다.
- 관리자는 팀/계정을 관리한다(팀 생성/수정/비활성/삭제, 계정 생성/초기화/삭제).

### 1.2 화면 구성
- `index.html`: 리포트 생성/미리보기/엑셀 다운로드
- `materials.html`: 소재 목록, 소재 요청 등록, 내 요청 내역, 팀별 소재목록 다운로드
- `approvals.html`: 승인 대기 요청 조회, 승인, 반려
- `admin.html`: 팀 관리 + 계정 관리 (관리자 전용)

### 1.3 역할
- `ADMIN`
- `TEAM_ADMIN`
- `TEAM_MEMBER`
- 미로그인 사용자

### 1.4 핵심 아키텍처
- 프론트: 정적 HTML/CSS/JS
- 조회 API: API Gateway + `query_handler` Lambda
- 쓰기 API: API Gateway + `write_handler` Lambda
- 저장소: S3 JSON
- 인증: 로그인 토큰(`Authorization: Bearer <token>`) 기반

---

## 2. 시스템 구조

### 2.1 조회 흐름
1. 로그인 후 프론트가 조회 API 호출 (`/report-data`, `/materials`, `/data-status`).
2. `query_handler`가 토큰 검증 및 권한 범위 적용.
3. S3 JSON 조회 후 응답 반환.
4. 프론트가 화면 렌더링, 리포트 집계/엑셀 생성은 브라우저에서 수행.

### 2.2 쓰기 흐름
1. 로그인 후 프론트가 쓰기 API 호출 (`/auth`, `/admin`, `/materials/requests`).
2. `write_handler`가 토큰/역할 검증.
3. 계정/팀/요청 JSON 저장소를 갱신.
4. 요청 `승인` 시 `materials/latest.json` 반영, `반려` 시 요청 상태만 갱신.

### 2.3 리포트 팀 범위 조회
- `ADMIN`: 전체 리포트 파일 기준 조회
- `TEAM_ADMIN`, `TEAM_MEMBER`: 팀별 리포트 파일 우선 조회
  - 팀별 파일 미존재 시 fallback 로직으로 조회 가능

### 2.4 배치와 소재 마스터
- 기본 모드(`s3_materials_latest`): `materials/latest.json`를 입력으로 리포트 생성
- 갱신 모드(`excel_refresh_materials`): `raw_list.xlsx`로 `materials/latest.json`를 재생성/덮어쓰기 후 리포트 생성

---

## 3. 화면별 기능

## 3.1 리포트 생성 (`index.html`)

### 접근 권한
- 미로그인: 화면은 보이지만 조회 차단
- 로그인 사용자: 조회 가능

### 주요 기능
- 기간 선택(수동 + 빠른선택)
- 집계 시트 선택
- 계산하기
- 미리보기 탭
- 엑셀 다운로드

### 데이터 흐름
- `GET /bti_revenue/data-status`
- `GET /bti_revenue/report-data?startDate=...&endDate=...`

### 지표/용어
- UI 라벨은 `순매출`
- `net_sales` 우선 사용, 없으면 `net_revenue`를 순매출 값으로 대체
- Raw 미리보기 `제품명`은 `mitem_name`
- `제품라인별` 집계에서 `product_name` 사용

---

## 3.2 소재 관리 (`materials.html`)

### 접근 권한
- 미로그인: 접근 불가
- 로그인 사용자: 접근 가능

### 상단 기능
- 팀별 소재목록 다운로드 (엑셀)
- 엑셀 일괄 등록 요청
- 소재 추가 신청

### 내부 탭
- `소재 목록`
  - 검색(`raw_cd`, `raw_nm`), 페이징, 수정/삭제 요청
- `내 요청 내역`
  - 본인 요청 전체 표시
  - 상태: `신청/완료/반려`
  - 요청일시/처리일시/처리자 표시

### 요청 차단 모드
- `BTI_MATERIAL_REQUESTS_ENABLED=false`일 때
  - 추가/수정/삭제/일괄등록 요청 생성 차단
  - 사용자 안내 팝업 표시

### 다운로드 컬럼 형식
- `team_id`, `comp_id`, `raw_cd`, `raw_nm`, `mmsta`, `raw_user_id`, `raw_user_nm`

### 데이터 흐름
- 목록 조회: `GET /bti_revenue/materials`
- 요청 생성: `POST /bti_revenue/materials/requests`
- 내 요청 조회: `GET /bti_revenue/materials/requests` + 클라이언트에서 본인 요청 필터

---

## 3.3 승인 요청 (`approvals.html`)

### 접근 권한
- `ADMIN`: 전체 팀 요청 조회/처리
- `TEAM_ADMIN`: 본인 팀 요청 조회/처리
- `TEAM_MEMBER`, 미로그인: 접근 불가

### 주요 기능
- 승인 대기(PENDING) 요청 조회
- `승인`
- `반려`
- 새로고침

### 데이터 흐름
- `GET /bti_revenue/materials/requests`
- `POST /bti_revenue/materials/requests/{requestId}/approve`
- `POST /bti_revenue/materials/requests/{requestId}/reject`

### 처리 규칙
- 승인: 요청 상태 `APPROVED`, 소재 마스터 반영
- 반려: 요청 상태 `REJECTED`, 소재 마스터 미반영
- 반려 사유: 미구현

---

## 3.4 관리자 (`admin.html`)

### 접근 권한
- `ADMIN`만 접근 가능

### 팀 관리
- 팀 목록 조회
- 팀 생성
- 팀명 수정
- 팀 비활성화
- 팀 삭제 (해당 팀 계정 cascade 삭제)

### 계정 관리
- 계정 목록 조회
- 일반 계정 생성(`TEAM_ADMIN`, `TEAM_MEMBER`)
- 비밀번호 초기화(`firstpassword`)
- 계정 삭제

### 정책
- `HQ`는 시스템 팀으로 수정/비활성화/삭제 불가
- 계정 생성은 활성 팀 드롭다운 선택 방식 (`HQ` 제외)
- 활성 계정이 있는 팀은 비활성화 차단

---

## 4. 인증/권한

### 4.1 로그인
- 별도 페이지 없이 모달 로그인
- 성공 시 토큰(`BTI_AUTH_TOKEN`)과 사용자(`BTI_AUTH_USER`) 저장

### 4.2 로그아웃
- 토큰/사용자 정보 제거 후 UI 갱신

### 4.3 비밀번호 변경
- 모든 로그인 사용자 가능
- 현재 비밀번호 검증 + 새 비밀번호(4자 이상)
- API: `POST /bti_revenue/auth/change-password`

### 4.4 역할별 탭 노출
| 역할 | 리포트 생성 | 소재 관리 | 승인 요청 | 관리자 |
|---|---|---|---|---|
| 미로그인 | 표시(조회 차단) | 비노출 | 비노출 | 비노출 |
| TEAM_MEMBER | 표시 | 표시 | 비노출 | 비노출 |
| TEAM_ADMIN | 표시 | 표시 | 표시 | 비노출 |
| ADMIN | 표시 | 표시 | 표시 | 표시 |

### 4.5 권한 체크 위치
- 프론트: 탭/화면 접근 가드
- 백엔드: 토큰 검증 + 역할 검증
  - `write_handler`: 쓰기 API
  - `query_handler`: 조회 API

---

## 5. API 명세

## 5.1 조회 API (`query_handler`)
- `GET /bti_revenue/report-data?startDate=...&endDate=...`
- `GET /bti_revenue/materials`
- `GET /bti_revenue/data-status`

## 5.2 쓰기 API (`write_handler`)

### 인증
- `POST /bti_revenue/auth/login`
- `POST /bti_revenue/auth/change-password`

### 관리자 계정
- `GET /bti_revenue/admin/accounts`
- `POST /bti_revenue/admin/accounts`
- `DELETE /bti_revenue/admin/accounts/{accountId}`
- `POST /bti_revenue/admin/accounts/{accountId}/reset-password`

### 관리자 팀
- `GET /bti_revenue/admin/teams`
- `POST /bti_revenue/admin/teams`
- `PATCH /bti_revenue/admin/teams/{teamId}`
- `POST /bti_revenue/admin/teams/{teamId}/deactivate`
- `DELETE /bti_revenue/admin/teams/{teamId}`

### 소재 요청
- `GET /bti_revenue/materials/requests`
- `POST /bti_revenue/materials/requests`
- `POST /bti_revenue/materials/requests/{requestId}/approve`
- `POST /bti_revenue/materials/requests/{requestId}/reject`

공통:
- `/auth/login` 제외 `Authorization: Bearer <token>` 필요
- CORS preflight(OPTIONS) 필요

---

## 6. 저장소/데이터 흐름

### 6.1 S3 주요 파일
#### 조회/배치
- `report/latest.json`
- `report/teams/{teamId}/latest.json`
- `materials/latest.json`
- `meta/latest.json`

#### 쓰기 API
- `auth/accounts.json`
- `auth/teams.json`
- `materials/requests_store.json`

### 6.2 로컬 저장소(보조)
- `BTI_AUTH_TOKEN`
- `BTI_AUTH_USER`
- fallback용: `BTI_ACCOUNTS`, `BTI_SESSION`, `BTI_MATERIALS_STORE_V1`

### 6.3 배치 메타(예시)
- `availableYears`
- `availableTeams`
- `teamReportRowCounts`
- `materialSource`
- `materialsRefreshedFromExcel`

---

## 7. 데이터 모델 요약

## 7.1 리포트 row
- `raw_cd`, `raw_nm`, `raw_ratio`
- `mitem_code`, `mitem_name`, `product_name`
- `customer_code`, `customer_name`
- `base_time`
- `product_sales_revenue`
- `net_sales` / `net_revenue`

## 7.2 소재 row
- `team_id`, `team_name`
- `comp_id`
- `raw_cd`, `raw_nm`, `mmsta`
- `raw_user_id`, `raw_user_nm`
- `researcher`, `created`, `approval_status`

## 7.3 요청 row
- `request_id`
- `request_type` (`CREATE|UPDATE|DELETE`)
- `request_status` (`PENDING|APPROVED|REJECTED`)
- `team_id`
- `requested_by_*`
- `payload`
- `approved_by_*`, `approved_at`
- `rejected_by_*`, `rejected_at`
- `created_at`

## 7.4 계정 row
- `account_id`, `login_id`, `name`
- `team_id`, `team_name`
- `role`, `active`

## 7.5 팀 row
- `team_id`, `team_name`
- `active`, `is_system`
- `created_at`, `updated_at`, `created_by_*`

---

## 8. 운영 주의사항

1. CORS/OPTIONS 설정 누락 시 브라우저에서 `Failed to fetch` 발생 가능
2. 조회/쓰기 Lambda의 `BTI_AUTH_SECRET`는 반드시 동일해야 함
3. `excel_refresh_materials` 모드는 `materials/latest.json`를 엑셀 기준으로 덮어씀
4. `MATERIAL_SOURCE_MODE` 운영값을 주기 실행 전에 확인 필요
5. JS 캐시 이슈 방지를 위해 캐시버스터 적용 중
   - `auth.js?v=20260225a`
   - `api-client.js?v=20260225b`
   - `materials-store.js?v=20260225b`
6. 반려 사유는 현재 미구현

---

## 9. 수동 검증 체크리스트

## 9.1 인증/권한
- 역할별 탭 노출
- 로그인/로그아웃
- 비밀번호 변경

## 9.2 리포트
- `/data-status` 연도 로딩
- 계산하기/미리보기/엑셀
- 팀 범위 조회(`ADMIN` 전체, 일반 사용자 본인 팀)

## 9.3 소재/요청
- 소재 목록 조회/검색/페이징
- 요청 생성(차단 모드 ON/OFF)
- `내 요청 내역` 탭 상태 표시(`신청/완료/반려`)
- 팀별 소재목록 다운로드

## 9.4 승인 요청
- 승인 대기 목록 조회
- 승인 처리
- 반려 처리
- 팀 권한 범위 검증

## 9.5 관리자
- 팀 CRUD/비활성/삭제(cascade)
- 계정 생성/초기화/삭제
- 정책(`HQ` 보호, 활성계정 팀 비활성화 차단)

---

## 10. 향후 개선 후보
- 반려 사유 입력/저장
- 승인 이력/감사 로그
- fallback(localStorage) 경로 축소
- SSO 연동
- 서버사이드 엑셀 생성/대용량 최적화

# BTI 소재 기반 매출 요약 사이트 기능명세서 (현재 구현 기준)

## 1. 한눈에 보기 (요약)

### 1.1 이 사이트가 하는 일
- 기간을 선택해 매출 데이터를 조회하고 요약 리포트를 미리보기/엑셀로 다운로드한다.
- 팀 소재 목록을 조회하고 소재 추가/수정/삭제 요청을 등록한다.
- 관리자/팀 관리자가 소재 요청을 승인한다.
- 관리자는 팀을 생성/수정/비활성/삭제하고, 일반 계정(팀 관리자/팀원)을 생성/삭제/비밀번호 초기화한다.

### 1.2 화면 구성 (현재 구현)
- `index.html`: 리포트 생성/미리보기/엑셀 다운로드
- `materials.html`: 소재 목록 조회 + 소재 요청 등록
- `approvals.html`: 승인 요청 조회/승인
- `admin.html`: 팀 관리 + 계정 목록 조회/생성/삭제/비밀번호 초기화 (관리자 전용)

### 1.3 역할 (현재 구현)
- `ADMIN` (관리자)
- `TEAM_ADMIN` (팀 관리자)
- `TEAM_MEMBER` (팀원)
- 미로그인 사용자

### 1.4 핵심 구조 (현재 구현)
- 프론트: 정적 HTML/JS
- 조회 API: API Gateway + `query_handler` Lambda
- 쓰기 API: API Gateway + `write_handler` Lambda
- 저장소: S3 JSON
- 인증: 로그인 후 토큰(`Authorization: Bearer`) 기반

---

## 2. 현재 시스템 구조 (쉽게 이해하는 버전)

### 2.1 조회 흐름 (리포트/소재 목록/배치상태)
1. 사용자가 로그인한다.
2. 프론트가 조회 API 호출 (`/report-data`, `/materials`, `/data-status`)
3. 조회 Lambda(`query_handler`)가 토큰을 검증한다.
4. S3 JSON(`report/latest.json`, `materials/latest.json`, `meta/latest.json`)을 읽는다.
5. 프론트가 결과를 화면에 표시하고, 리포트는 브라우저에서 집계/엑셀 생성한다.

### 2.2 쓰기 흐름 (계정/소재요청/승인)
1. 사용자가 로그인한다.
2. 프론트가 쓰기 API 호출 (`/auth`, `/admin`, `/materials/requests`)
3. 쓰기 Lambda(`write_handler`)가 토큰과 역할을 검증한다.
4. S3 JSON에 계정/요청 데이터를 저장 또는 갱신한다.
5. 승인 시 `materials/latest.json`에 실제 소재 목록 반영까지 수행한다.
6. 팀 관리 시 `auth/teams.json`에 팀 마스터를 저장/갱신하고, 팀 삭제 시 해당 팀 계정을 일괄 삭제한다.

### 2.3 데이터 소스 우선순위 (프론트)
- 1순위: API (`api-config.js` 또는 `localStorage.BTI_API_BASE_URL` 설정 시)
- 2순위: 샘플 fallback (`data.js`) — 일부 화면/상황에서 보조용

---

## 3. 화면별 기능 요약

## 3.1 리포트 생성 화면 (`index.html`)

### 목적
- 기간과 집계 방식을 선택해 리포트 미리보기와 엑셀 다운로드를 수행한다.

### 접근 권한
- 미로그인: 화면 UI는 보이지만 조회 차단
- 로그인(`ADMIN`, `TEAM_ADMIN`, `TEAM_MEMBER`): 조회 가능

### 주요 기능
- 기간 선택 (수동 날짜 + 빠른선택)
- 집계 시트 선택 (Raw, 총매출, 월별, 분기별, 반기별, 소재별, 제품라인별, 고객별, 제형별)
- `계산하기` 실행
- 미리보기 탭 표시 (상위 10건)
- 엑셀 다운로드

### 빠른선택 연도 목록 규칙
- `/data-status.availableYears` 우선 사용
- 실패/없음 시 fallback: 현재연도, 현재연도-1, 현재연도-2

### 데이터 흐름
- `GET /bti_revenue/data-status` → 빠른선택 연도 목록
- `GET /bti_revenue/report-data?startDate=...&endDate=...` → 리포트 원천 데이터
- 프론트(`data.js`)에서 집계 계산 후 미리보기/엑셀 생성

### 팀 범위 규칙 (현재 구현)
- `ADMIN`: 전체 팀 리포트 조회
- `TEAM_ADMIN`, `TEAM_MEMBER`: 본인 팀 소재(`raw_cd`) 기준 row만 조회

### 현재 구현상 중요한 용어
- UI 라벨은 `순매출`
- 데이터는 `net_sales`를 우선 사용하고, 없으면 `net_revenue`를 순매출 값으로 대체 사용
- Raw 미리보기의 `제품명`은 `mitem_name`
- `제품라인별` 집계에서만 `product_name` 사용

---

## 3.2 소재 관리 화면 (`materials.html`)

### 목적
- 소재 목록을 조회하고, 소재 추가/수정/삭제 요청을 등록한다.

### 접근 권한
- 미로그인: 접근 불가
- 로그인 사용자(`ADMIN`, `TEAM_ADMIN`, `TEAM_MEMBER`): 접근 가능

### 주요 기능
- 소재 목록 조회
- 검색 (`raw_cd`, `raw_nm`)
- 페이징 (기본 10건)
- 단건 소재 추가 신청
- 단건 소재 수정 신청
- 단건 소재 삭제 신청
- 엑셀 일괄 등록 요청

### 데이터 흐름
- 초기 목록 조회: `GET /bti_revenue/materials`
- 소재 요청 생성: `POST /bti_revenue/materials/requests`
- API 사용 불가 시 `materials-store.js` localStorage fallback 경로 존재

### 현재 구현 메모
- API 모드에서는 요청 생성 후 목록은 `/materials` 재조회로 갱신
- 승인 전 요청은 `승인 요청` 탭에서 처리
- `ADMIN`은 전체 팀 소재 목록 조회, 일반 사용자는 본인 팀 소재만 조회

---

## 3.3 승인 요청 화면 (`approvals.html`)

### 목적
- 소재 추가/수정/삭제 요청을 조회하고 승인한다.

### 접근 권한
- `ADMIN`: 전체 팀 요청 조회/승인 가능
- `TEAM_ADMIN`: 본인 팀 요청만 조회/승인 가능
- `TEAM_MEMBER`, 미로그인: 접근 불가

### 주요 기능
- 승인 대기 요청 목록 조회
- 요청 승인 (`승인`만 존재, `반려`는 미구현)
- 새로고침

### 데이터 흐름
- `GET /bti_revenue/materials/requests`
- `POST /bti_revenue/materials/requests/{requestId}/approve`
- 승인 시 `materials/latest.json` 반영 + 요청 상태 업데이트

---

## 3.4 관리자 화면 (`admin.html`)

### 목적
- 팀 마스터 관리 + 일반 계정(팀 관리자/팀원) 관리

### 접근 권한
- `ADMIN`만 접근 가능
- 그 외 사용자/미로그인: 접근 불가

### 주요 기능
#### 팀 관리
- 팀 목록 조회
- 팀 생성
- 팀명 수정
- 팀 비활성화
- 팀 삭제 (해당 팀 계정 일괄 삭제)

#### 계정 관리
- 계정 목록 조회
- 일반 계정 생성 (`TEAM_ADMIN`, `TEAM_MEMBER`)
- 일반 계정 비밀번호 초기화
- 일반 계정 삭제

### 현재 구현 규칙
- `HQ`는 시스템 팀으로 수정/비활성화/삭제 대상 아님
- 계정 생성 시 팀은 직접입력이 아니라 `팀 선택` 드롭다운으로만 지정
- 계정 생성 드롭다운에는 활성 팀만 표시되며 `HQ`는 제외
- 비활성 팀은 계정 생성 대상에서 제외
- 팀 비활성화는 해당 팀에 활성 계정이 있으면 차단
- 팀 삭제 시 해당 `team_id` 계정이 일괄 삭제됨 (cascade)
- 관리자(`ADMIN`) 계정은 관리자 화면에서 삭제 불가
- 관리자(`ADMIN`) 계정은 관리자 화면에서 비밀번호 초기화 대상 아님
- 초기화 비밀번호 기본값: `firstpassword`

### 데이터 흐름
- `GET /bti_revenue/admin/teams`
- `POST /bti_revenue/admin/teams`
- `PATCH /bti_revenue/admin/teams/{teamId}`
- `POST /bti_revenue/admin/teams/{teamId}/deactivate`
- `DELETE /bti_revenue/admin/teams/{teamId}` (팀 삭제 + 계정 일괄 삭제)
- `GET /bti_revenue/admin/accounts`
- `POST /bti_revenue/admin/accounts`
- `POST /bti_revenue/admin/accounts/{accountId}/reset-password`
- `DELETE /bti_revenue/admin/accounts/{accountId}`

---

## 4. 인증/권한 (현재 구현)

## 4.1 로그인 방식
- 별도 로그인 페이지 없음
- 헤더 우측 `로그인` 버튼 → 모달 입력(ID/PW)
- 로그인 성공 시:
  - 팀/이름 표시
  - 역할별 탭 노출 적용
  - 토큰 저장 (`BTI_AUTH_TOKEN`)
  - 사용자 정보 저장 (`BTI_AUTH_USER`)

## 4.2 로그아웃
- 헤더 우측 `로그아웃`
- 토큰/사용자 정보 제거 후 화면 재로드

## 4.3 본인 비밀번호 변경
- 모든 로그인 계정 가능 (`ADMIN`, `TEAM_ADMIN`, `TEAM_MEMBER`)
- 헤더 우측 `비밀번호 변경` 버튼
- 입력: 현재 비밀번호, 새 비밀번호
- 검증: 현재 비밀번호 일치, 새 비밀번호 4자 이상
- API: `POST /bti_revenue/auth/change-password`

## 4.4 역할별 탭 노출 규칙

| 역할 | 리포트 생성 | 소재 관리 | 승인 요청 | 관리자 |
|---|---|---|---|---|
| 미로그인 | 표시(조회 불가) | 비노출 | 비노출 | 비노출 |
| TEAM_MEMBER | 표시 | 표시 | 비노출 | 비노출 |
| TEAM_ADMIN | 표시 | 표시 | 표시 | 비노출 |
| ADMIN | 표시 | 표시 | 표시 | 표시 |

## 4.5 권한 체크 위치
- 프론트: 탭 노출/화면 접근/UI 차단
- 백엔드(Lambda): 토큰 검증 + 역할 검증
  - 쓰기 API: `write_handler`
  - 조회 API: `query_handler`

---

## 5. API 명세 (현재 구현 사용분)

## 5.1 조회 API (Query Lambda)
대상 Lambda: `query_handler`

- `GET /bti_revenue/report-data?startDate=...&endDate=...`
  - 리포트 원천 데이터 반환
- `GET /bti_revenue/materials`
  - 소재 목록 반환
- `GET /bti_revenue/data-status`
  - 배치 상태/연도목록(`availableYears`) 반환

공통사항:
- `Authorization: Bearer <token>` 필요
- CORS preflight(OPTIONS) 필요

## 5.2 쓰기 API (Write Lambda)
대상 Lambda: `write_handler`

### 인증
- `POST /bti_revenue/auth/login`
- `POST /bti_revenue/auth/change-password` (인증 필요)

### 관리자 계정
- `GET /bti_revenue/admin/accounts`
- `POST /bti_revenue/admin/accounts`
- `DELETE /bti_revenue/admin/accounts/{accountId}`
- `POST /bti_revenue/admin/accounts/{accountId}/reset-password`

### 관리자 팀 관리
- `GET /bti_revenue/admin/teams`
- `POST /bti_revenue/admin/teams`
- `PATCH /bti_revenue/admin/teams/{teamId}`
- `POST /bti_revenue/admin/teams/{teamId}/deactivate`
- `DELETE /bti_revenue/admin/teams/{teamId}`

### 소재 요청/승인
- `GET /bti_revenue/materials/requests`
- `POST /bti_revenue/materials/requests`
- `POST /bti_revenue/materials/requests/{requestId}/approve`

공통사항:
- `/auth/login` 제외 `Authorization: Bearer <token>` 필요
- CORS preflight(OPTIONS) 필요

---

## 6. 데이터 저장 위치 / 데이터 흐름 (현재 구현)

## 6.1 S3 저장 데이터 (주요)
### 조회 데이터
- `report/latest.json` : 리포트 원천 데이터
- `materials/latest.json` : 승인 반영된 소재 목록
- `meta/latest.json` : 배치 상태/건수/availableYears

### 쓰기 API 데이터
- `auth/accounts.json` : 계정 목록
- `auth/teams.json` : 팀 마스터 목록
- `materials/requests_store.json` : 승인 요청 목록/상태

> 실제 버킷/경로 prefix는 환경변수(`BTI_*`)로 결정됨

## 6.2 프론트 로컬 저장소 (현재 구현, 보조)
### 인증 관련
- `BTI_AUTH_TOKEN` : 로그인 토큰
- `BTI_AUTH_USER` : 로그인 사용자 정보

### fallback/개발용 저장소 (일부 경로)
- `BTI_ACCOUNTS`
- `BTI_SESSION`
- `BTI_MATERIALS_STORE_V1`

설명:
- API 미설정 또는 fallback 경로에서 사용됨
- 운영 데이터의 주 저장소로 사용하지 않음

---

## 7. 주요 데이터 모델 (프론트 기준 요약)

## 7.1 리포트 row (일부)
- `raw_cd`, `raw_nm`, `raw_ratio`
- `mitem_code`, `mitem_name`
- `product_name`
- `customer_code`, `customer_name`
- `base_time`
- `product_sales_revenue`
- `net_sales` (없으면 `net_revenue` 대체)
- `net_revenue`

## 7.2 소재 row (일부)
- `raw_cd`
- `raw_nm`
- `mmsta`
- `researcher`
- `created`
- `approval_status`
- `team_id`
- `team_name`

## 7.3 승인 요청 row (쓰기 API 기준)
- `request_id`
- `request_type` (`CREATE|UPDATE|DELETE`)
- `request_status` (`PENDING|APPROVED`)
- `team_id`
- `requested_by_*`
- `payload` (소재 정보)
- `approved_by_*`
- `approved_at`
- `created_at`

## 7.4 계정 row (쓰기 API 기준)
- `account_id`
- `login_id`
- `name`
- `team_id`, `team_name`
- `role`
- `active`
- (서버 저장 시) `password`는 해시 저장

## 7.5 팀 row (쓰기 API 기준)
- `team_id`
- `team_name`
- `active`
- `is_system` (`HQ` 등 시스템 팀)
- `created_at`, `updated_at`
- `created_by_*`

---

## 8. 현재 제약사항 / 운영 주의사항

## 8.1 CORS / OPTIONS 설정 필수
- 브라우저에서 `Authorization` 헤더를 사용하므로 preflight(`OPTIONS`)가 발생함
- 모든 사용 경로에 `OPTIONS` 메서드 및 CORS 설정 필요

## 8.2 조회/쓰기 Lambda 토큰 비밀키 일치 필요
- `BTI_AUTH_SECRET` 값이 조회 Lambda와 쓰기 Lambda에서 동일해야 함
- 다르면 로그인은 되더라도 조회 API가 403 발생 가능

## 8.3 승인 기능 범위
- 현재는 `승인`만 구현
- `반려`/반려사유는 미구현

## 8.4 리포트/소재 데이터 팀 분리 기준
- 로그인 여부/역할 기반 조회 허용은 구현됨
- `ADMIN`: 전체 팀 데이터 조회
- `TEAM_ADMIN`, `TEAM_MEMBER`: 본인 팀 데이터만 조회
- 리포트 팀 분리 기준은 `raw_cd -> 소재(team_id)` 매핑 기준
- 팀 정보가 없는 기존 소재 row는 호환을 위해 `MB2`로 기본 보정됨

## 8.5 fallback 로직 존재
- API 미설정/실패 시 일부 화면은 샘플 또는 localStorage fallback 사용 가능
- 운영 환경에서는 API 경로 기준으로 동작하도록 관리 필요

---

## 9. 수동 검증 체크리스트 (운영 전 점검용)

## 9.1 로그인/권한
- 미로그인 시 `리포트 생성`만 보이는지
- 로그인 후 역할별 탭 노출이 맞는지
- 로그아웃 시 토큰 제거/탭 변경이 되는지
- 본인 비밀번호 변경이 되는지

## 9.2 리포트 화면
- `/data-status` 기반 빠른선택 연도 로딩
- `계산하기` 정상 동작
- 미리보기 탭 생성
- 순매출 값 정상 표시 (`net_sales` 또는 `net_revenue` 대체)
- 엑셀 다운로드 버튼 활성화/다운로드

## 9.3 소재 요청/승인
- 소재 추가/수정/삭제 요청 생성
- 승인 요청 탭에서 요청 조회
- 승인 처리 후 요청 목록에서 제거
- 승인 후 `materials` 목록에 반영

## 9.4 관리자 계정 관리
- 계정 목록 조회
- 팀 목록 조회/생성/수정/비활성화/삭제
- 일반 계정 생성
  - 팀 선택 드롭다운(활성 팀만, `HQ` 제외)
- 일반 계정 비밀번호 초기화 (`firstpassword`)
- 일반 계정 삭제
- 팀 삭제 시 해당 팀 계정 일괄 삭제(cascade)
- 관리자 계정은 삭제/초기화 제한이 적용되는지
- 활성 계정이 있는 팀 비활성화 차단 동작 확인

## 9.5 CORS/API 배포
- 브라우저에서 `Failed to fetch` 없이 동작하는지
- 사용 경로별 `OPTIONS`/CORS가 모두 설정되었는지

---

## 10. 향후 개선 후보 (미구현)
- 승인 `반려` 기능 및 반려 사유
- 승인 이력/감사 로그
- 리포트 데이터 팀별 접근 제한
- SSO 연동
- fallback(localStorage) 경로 축소 또는 제거
- 서버사이드 엑셀 생성/대용량 최적화

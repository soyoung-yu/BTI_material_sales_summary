# BTI_material_sales_summary

팀별 개발 소재 기반 매출 집계 리포트의 **정적 HTML 프로토타입**입니다. 브라우저에서 리포트 생성, 집계 미리보기, 엑셀 다운로드와 소재 관리 화면을 확인할 수 있습니다. 백엔드/DB는 아직 없으며, 모든 데이터는 `data.js`의 목업을 사용합니다.

**프로젝트 한눈에 보기**
- 화면
  - `index.html`: 리포트 생성/집계 미리보기/엑셀 다운로드
  - `materials.html`: 소재 목록 관리(검색/필터/추가/수정/삭제)
- 데이터
  - `data.js`: 목업 데이터(`RAW_SALES_DATA`, `MATERIALS`) + 집계 함수
- 빌드/런타임
  - 정적 파일만 사용. 의존성은 CDN(ExcelJS) 1개.

**실행 방법**
1. 로컬에서 `index.html`을 브라우저로 열면 리포트 생성 화면을 확인할 수 있습니다.
2. `materials.html`에서 소재 관리 화면을 확인할 수 있습니다.

**현재 동작 흐름(데이터 → 집계 → 미리보기 → 엑셀)**
1. 사용자가 기간/집계 방식을 선택하고 `계산하기` 클릭
2. `RAW_SALES_DATA`를 날짜 범위로 필터링
3. 선택된 집계 방식에 따라 집계 함수 실행
4. 탭별 미리보기 테이블 렌더링
5. `ExcelJS`로 동일 로직의 시트를 생성해 다운로드

**중복 제거/집계 기준(핵심 로직 요약)**
- 기본 중복 제거 키: `mitem_code + customer_code + base_time`
- `aggregateTotal`, `aggregateByMonth`, `aggregateByQuarter`, `aggregateByHalf`, `aggregateByProductLine`, `aggregateByCustomer`, `aggregateByFormulation`은 위 키 기준으로 중복 제거 후 합산
- `aggregateByMaterial`은 소재 기여도 파악을 위해 **중복 제거 없이** 합산
- `revenue_share` 계산은 `aggregateTotal` 기준의 중복 제거 총매출을 분모로 사용

**집계 시트/탭 구조**
- 기본 포함: `Raw`
- 선택 가능: `Summary_총매출`, `Summary_월별`, `Summary_분기별`, `Summary_반기별`, `Summary_소재별`, `Summary_제품라인별`, `Summary_고객별`, `Summary_제형별`

**엑셀 출력 포맷**
- 헤더: 진한 남색 배경, 흰색 글씨, 가운데 정렬, 볼드
- 테두리: 모든 셀 얇은 테두리
- 줄무늬: 짝수 행 연한 회색 배경
- 숫자 포맷: 매출 천단위, 비율 퍼센트
- 정렬: 숫자 우측, 텍스트 좌측
- 컬럼 너비: 고정/정의값 사용
- 필터/고정: 헤더 행 필터 + 첫 행 고정

**화면별 주요 상태/동작 포인트**
- `index.html`
  - 상태: `filteredData`, `aggregatedData`
  - 입력: 기간(`startDate`, `endDate`), 빠른 선택(`quickSelect`)
  - 주요 함수: `calculateData`, `renderPreviewTabs`, `downloadExcel`
- `materials.html`
  - 상태: `materials`, `filteredMaterials`, `currentPage`, `pageSize`
  - 입력: 검색/상태 필터
  - 주요 함수: `filterAndRender`, `renderTable`, `renderPagination`, `openAddModal`, `openEditModal`

**파일 구성**
- `index.html`: 리포트 생성 UI/로직
- `materials.html`: 소재 관리 UI/로직
- `data.js`: 목업 데이터 및 집계 함수
- `sample_df.csv`: 목업 데이터 원본 샘플
- `service_spec.md`: 서비스 요구사항/기획 메모
- `251Q_MB2_revenue_report.xlsx`: 예시 리포트 파일
- `BTI_revenue_tracking_by_raw_ver2.ipynb`: 데이터 분석/검증용 노트북

**확장/수정 시 유의사항(바로 작업 시작 가이드)**
- 데이터 필드 추가/변경
  - `data.js`의 `RAW_SALES_DATA` 스키마와 `index.html`의 테이블/엑셀 컬럼을 함께 수정
- 집계 로직 변경
  - `data.js` 집계 함수가 소스이므로, 변경 시 미리보기/엑셀 모두 자동 반영
- 시트 추가
  - `index.html`에서 체크박스 옵션 추가
  - `calculateData`의 `switch`에 집계 함수 연결
  - `downloadExcel`의 `switch`에 컬럼 정의 추가
- UI 변경
  - 별도 빌드 도구 없음. `index.html`, `materials.html`을 직접 수정

**향후 연동 지점(백엔드/DB)**
- 데이터 소스: Athena 쿼리 → FastAPI로 조회
- 소재 관리: 내부 DB(PostgreSQL 등) CRUD API 예정
- 사용자 인증: 실제 서비스에선 `user_name`, `dept_id` 기반 접근 제어
- 프론트엔드: Next.js + React로 전환 예정

**참고**
- 본 프로젝트는 정적 프로토타입이며 백엔드는 포함하지 않습니다.
- 상세 요구사항은 `service_spec.md`를 확인하세요.

**README 업데이트 가이드**
- 이 README는 “프로젝트를 다시 시작하는 사람이 README만 읽고 바로 수정 가능”하도록 유지합니다.
- 개발 완료 후 아래 항목을 점검/업데이트하세요.
  - 변경된 기능/화면/파일이 있으면 `프로젝트 한눈에 보기`, `파일 구성`, `화면별 주요 상태/동작 포인트` 반영
  - 집계 로직이 바뀌면 `중복 제거/집계 기준`, `집계 시트/탭 구조`, `엑셀 출력 포맷` 수정
  - 데이터 스키마가 바뀌면 `확장/수정 시 유의사항`과 관련 설명에 반영
  - 실행 방식(로컬/배포/의존성)이 바뀌면 `실행 방법` 수정
  - 향후 연동 지점이 변경되면 `향후 연동 지점` 업데이트

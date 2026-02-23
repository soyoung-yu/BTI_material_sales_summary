# BTI Material Sales Summary

BTI 팀 개발 소재 기반 매출 리포트 프로젝트입니다.  
현재는 정적 프론트엔드(`index.html`, `materials.html`) + AWS API Gateway/Lambda/S3 기반 조회/배치 구조로 운영하도록 전환 중입니다.

이 문서는 담당자가 바뀌어도 아래를 바로 이해할 수 있도록 작성되었습니다.
- 시스템 구조(어디서 데이터를 만들고 어디서 조회하는지)
- 배포/운영 방식(로컬 테스트, AWS 연동, 사내 EC2 배포)
- 필수 환경변수/권한
- 장애 발생 시 확인 순서

## 1. 현재 운영 구조 (핵심)

### 전체 흐름
1. 사용자는 브라우저에서 리포트 화면/소재 화면 사용
2. 프론트는 `API Gateway`를 호출
3. 조회용 Lambda가 `S3`의 JSON(`report/materials/meta`)을 읽어 응답
4. 프론트는 받은 `report` 원천 데이터를 기준으로 집계/미리보기/엑셀 생성

### 배치 흐름 (일배치)
1. `EventBridge Scheduler`가 매일 자정(KST)에 배치용 Lambda 실행
2. 배치용 Lambda가 `Athena` 조회 + 전처리 수행
3. 결과를 S3에 저장
   - `report/latest.json` (리포트 원천 데이터)
   - `materials/latest.json` (소재 목록)
   - `meta/latest.json` (배치 상태/건수/시각)

### 중요한 개념 구분
- `report/latest.json`: 집계 결과가 아니라 **집계 가능한 전처리 원천 데이터**
- `materials/latest.json`: 소재 목록 데이터
- `meta/latest.json`: 배치 성공/실패, 마지막 생성시각, 건수 등 **운영 메타데이터**

## 2. 현재 상태 (개발/운영 기준)

### 완료된 항목
- 프론트가 `API Gateway` 기반 조회를 사용할 수 있도록 구현됨
- `query_handler` Lambda로 `/report-data`, `/materials`, `/data-status` 응답 가능
- `sample_df.csv` 기반 테스트용 JSON 생성 스크립트 제공 (`make_sample_json.py`)
- 배치용 Lambda 스캐폴딩 + 노트북 기반 전처리 로직 일부 이식 완료
- `net_sales`는 현재 단계에서 UI/엑셀에서 제외 (추후 추가 예정)

### 진행 중/주의사항
- 배치 Lambda는 데이터량에 따라 메모리 크게 필요할 수 있음 (512MB 부족 가능)
- `MATERIAL_LIST_S3_PATH`(팀 관리소재 엑셀 S3 경로) 필요
- IAM 권한(특히 배치 Lambda `s3:PutObject`) 없으면 S3 저장 실패
- SageMaker 연동은 현재 코드에 미포함(추후 필요 시 추가)

## 3. 프로젝트 파일 구조 (실사용 중심)

### 프론트
- `index.html`: 리포트 생성/집계 미리보기/엑셀 다운로드
- `materials.html`: 소재 목록 화면
- `data.js`: 집계 함수 + 샘플 데이터(fallback)
- `api-client.js`: API Gateway 호출 공통 클라이언트
- `api-config.js`: 로컬/사내 테스트용 기본 API 설정 (빈 값)
- `api-config.example.js`: API 설정 예시

### 백엔드 (AWS Lambda용 코드)
- `backend/lambdas/query_handler.py`: 조회용 Lambda 핸들러 (API Gateway 연결)
- `backend/lambdas/batch_handler.py`: 배치용 Lambda 핸들러 (EventBridge 연결)
- `backend/batch/pipeline.py`: 배치 파이프라인 본체 (Athena/BOM/전처리/S3 저장용 row 생성)
- `backend/batch/queries.py`: Athena SQL 생성 함수
- `backend/batch/transformers.py`: 전처리 유틸 (BOM closure, 제품명 정규화 등)
- `backend/requirements.txt`: Python 의존성 목록

### 데이터/샘플/분석
- `sample_df.csv`: 리포트 원천 샘플 CSV
- `make_sample_json.py`: `sample_df.csv` -> `out/*/latest.json` 생성 스크립트
- `BTI_revenue_tracking_by_raw_ver3.ipynb`: 분석/검증용 노트북(운영 코드는 아님)

## 4. AWS 리소스 구성 (권장 운영)

### 조회 경로
- API Gateway (REST API)
  - `/bti_revenue/report-data`
  - `/bti_revenue/materials`
  - `/bti_revenue/data-status`
- Lambda (조회용)
  - 핸들러: `backend.lambdas.query_handler.lambda_handler`

### 배치 경로
- EventBridge Scheduler (매일 00:00 KST)
- Lambda (배치용)
  - 핸들러: `backend.lambdas.batch_handler.lambda_handler`

### 저장소
- S3 버킷: 예) `<YOUR_S3_BUCKET>`
- 프로젝트 prefix: 예) `<YOUR_PROJECT_PREFIX>/bti_revenue/`

## 5. S3 데이터 구조 (현재 구현 기준)

### 조회용 latest 파일
- `<YOUR_PROJECT_PREFIX>/bti_revenue/report/latest.json`
- `<YOUR_PROJECT_PREFIX>/bti_revenue/materials/latest.json`
- `<YOUR_PROJECT_PREFIX>/bti_revenue/meta/latest.json`

### 배치 버전 파일
- `<YOUR_PROJECT_PREFIX>/bti_revenue/report/versions/{batchId}.json`
- `<YOUR_PROJECT_PREFIX>/bti_revenue/materials/versions/{batchId}.json`

### 입력 파일 (배치용)
- `<YOUR_PROJECT_PREFIX>/bti_revenue/materials/raw_list.xlsx` (팀 관리 소재 엑셀)

## 6. JSON 포맷 (현재 조회 Lambda 기대 포맷)

### report/latest.json
```json
{
  "rows": [
    {
      "raw_cd": "6034078",
      "raw_nm": "원료명",
      "raw_ratio": 0.01,
      "mitem_code": "9XXXX",
      "mitem_name": "제품명",
      "category": "FERT",
      "forml_code": "11S....",
      "forml_name": "제형명",
      "customer_code": "100001",
      "customer_name": "고객사명",
      "base_time": "2025-01-01",
      "total_revenue": 1000000,
      "product_sales_revenue": 1000000,
      "net_revenue": 300000,
      "product_name": "정규화제품명"
    }
  ],
  "meta": {
    "batchId": "20260223T000000Z",
    "generatedAt": "2026-02-23T00:00:00Z",
    "status": "success",
    "rowCount": 110
  }
}
```

### materials/latest.json
```json
{
  "rows": [
    {
      "raw_cd": "6034078",
      "raw_nm": "원료명",
      "mmsta": "",
      "researcher": "",
      "created": "2026-02-23",
      "approval_status": "완료"
    }
  ],
  "meta": {
    "batchId": "20260223T000000Z",
    "generatedAt": "2026-02-23T00:00:00Z",
    "status": "success",
    "rowCount": 10
  }
}
```

### meta/latest.json
```json
{
  "status": "success",
  "batchId": "20260223T000000Z",
  "lastSuccessAt": "2026-02-23T00:00:00Z",
  "reportRowCount": 110,
  "materialsRowCount": 10
}
```

## 7. 프론트 동작 방식 (현재)

### API 우선 + 샘플 fallback
- `api-client.js`가 API Base URL이 설정되어 있으면 API 호출
- API Base URL이 없으면 `data.js`의 샘플 데이터 fallback 사용

### API Base URL 설정 방법 (로컬/사내 테스트)
브라우저 콘솔에서:
```js
localStorage.setItem('BTI_API_BASE_URL', 'https://{api-id}.execute-api.{region}.amazonaws.com/{stage}/bti_revenue')
```

### net_sales 처리 (현재 정책)
- `net_sales`는 현재 단계에서 미구현
- UI/엑셀에서 `net_sales` 관련 컬럼 숨김 처리
- 집계 함수는 `net_sales` 누락 데이터에도 동작하도록 방어 처리됨

## 8. 로컬 테스트 방법

### 1) 정적 서버 실행
```bash
python3 -m http.server 8000
```

### 2) API 연결
- 브라우저 콘솔에서 `localStorage.BTI_API_BASE_URL` 설정 (위 예시)

### 3) 화면 확인
- `http://localhost:8000/index.html`
- `http://localhost:8000/materials.html`

## 9. 샘플 데이터로 S3 테스트 JSON 만드는 방법

### 생성
```bash
python3 make_sample_json.py
```

### 생성 결과
- `out/report/latest.json`
- `out/materials/latest.json`
- `out/meta/latest.json`

### S3 업로드 예시
```bash
aws s3 cp out/report/latest.json s3://<YOUR_S3_BUCKET>/<YOUR_PROJECT_PREFIX>/bti_revenue/report/latest.json
aws s3 cp out/materials/latest.json s3://<YOUR_S3_BUCKET>/<YOUR_PROJECT_PREFIX>/bti_revenue/materials/latest.json
aws s3 cp out/meta/latest.json s3://<YOUR_S3_BUCKET>/<YOUR_PROJECT_PREFIX>/bti_revenue/meta/latest.json
```

## 10. Lambda 핸들러 설정 (중요)

### 조회용 Lambda (API Gateway 연결)
- 핸들러: `backend.lambdas.query_handler.lambda_handler`

### 배치용 Lambda (EventBridge 연결)
- 핸들러: `backend.lambdas.batch_handler.lambda_handler`

주의:
- 하나의 Lambda 함수에는 핸들러 1개만 설정 가능
- 조회용/배치용 Lambda는 **별도 함수**로 만드는 것을 권장
- 코드 ZIP은 동일하게 재사용 가능(핸들러만 다르게 설정)

## 11. Lambda 환경변수 (현재 자주 쓰는 값)

### 조회용 Lambda
- `BTI_DATA_BUCKET=<YOUR_S3_BUCKET>`
- `BTI_REPORT_LATEST_KEY=<YOUR_PROJECT_PREFIX>/bti_revenue/report/latest.json`
- `BTI_MATERIALS_LATEST_KEY=<YOUR_PROJECT_PREFIX>/bti_revenue/materials/latest.json`
- `BTI_META_LATEST_KEY=<YOUR_PROJECT_PREFIX>/bti_revenue/meta/latest.json`
- `ALLOWED_ORIGIN=*` (테스트용, 운영시 EC2 도메인으로 제한)

### 배치용 Lambda
- `BTI_DATA_BUCKET=<YOUR_S3_BUCKET>`
- `BTI_REPORT_PREFIX=<YOUR_PROJECT_PREFIX>/bti_revenue/report`
- `BTI_MATERIALS_PREFIX=<YOUR_PROJECT_PREFIX>/bti_revenue/materials`
- `BTI_META_PREFIX=<YOUR_PROJECT_PREFIX>/bti_revenue/meta`
- `MATERIAL_LIST_S3_PATH=s3://<YOUR_S3_BUCKET>/<YOUR_PROJECT_PREFIX>/bti_revenue/materials/raw_list.xlsx`
- `ATHENA_DATABASE=data_mart`
- `COMP_ID=1200`
- `CUSTOMER_COMP_ID=1200`
- `BATCH_LOOKBACK_MONTHS=24` (또는 `REPORT_START_DATE`, `REPORT_END_DATE`)
- `INCLUDE_NET_SALES=false`

## 12. EventBridge 스케줄 설정 (배치)

### 목표
- 매일 `00:00 KST` 배치 실행

### 권장 (EventBridge Scheduler)
- Time zone: `Asia/Seoul`
- Cron: `cron(0 0 * * ? *)`

### UTC로 설정해야 하는 경우
- KST 자정 = UTC 15:00 (전날)
- Cron: `cron(0 15 * * ? *)`

## 13. 권한 (IAM) 요약

### 조회용 Lambda 역할
- CloudWatch Logs
- VPC ENI 권한 (VPC 사용 시)
- S3 읽기 (`report/materials/meta latest.json`)

### 배치용 Lambda 역할
- CloudWatch Logs
- VPC ENI 권한
- S3 읽기/쓰기 (`<YOUR_PROJECT_PREFIX>/bti_revenue/*`)
- Athena 쿼리 실행 권한
- Glue Data Catalog 읽기 권한
- (조건부) Athena 결과 버킷 S3 권한
- (조건부) KMS 권한 (SSE-KMS 사용 시)
- (추후) SageMaker 권한

## 14. 운영/장애 대응 체크리스트 (실무용)

### A. API는 되는데 데이터가 안 나옴
1. `/bti_revenue/data-status` 호출
2. `meta/latest.json` 존재 여부 확인
3. Lambda 환경변수 key 경로 오타 확인
4. S3 key 실제 경로 확인

### B. `NoSuchKey`
- S3에 파일 없음 또는 key 오타
- `BTI_*_KEY`/prefix 재확인

### C. `AccessDenied` (S3)
- Lambda 역할에 `s3:GetObject` 또는 `s3:PutObject` 권한 부족

### D. 배치 Lambda OOM
- 메모리 증설 (권장 시작: 2048MB)
- Timeout 증설 (권장: 300초)
- 테스트 기간 축소

### E. `Missing optional dependency 'fsspec'`
- 현재 저장소 코드(`backend/batch/pipeline.py`)는 `pd.read_excel("s3://...")` 방식이라 `fsspec/s3fs`가 필요할 수 있음
- 운영 제약으로 레이어 추가가 어렵다면 `boto3 + BytesIO` 방식으로 코드 수정 검토

### F. `No module named backend`
- Lambda ZIP 루트에 `backend/` 폴더가 있어야 함
- 압축 루트 구조 확인

## 15. 사내 EC2 배포 운영 방식 (목표)

### 구조
- 사내 EC2에서 정적 파일 서빙 (`index.html`, `materials.html`, js 파일들)
- 브라우저는 API Gateway 호출
- 사내망에서만 EC2 접근 허용

### 운영 전 체크
- `ALLOWED_ORIGIN`을 EC2 도메인/호스트로 제한
- API Gateway CORS 설정 정리
- EC2에서 API URL 접근 가능 여부 확인

## 16. 향후 개선 후보

1. `raw_list.xlsx` 의존 제거
- 소재 목록을 DB/Athena 기반으로 전환

2. SageMaker 연동 추가
- 현재 배치 파이프라인에 SageMaker 단계 연결

3. 배치 성능 최적화
- BOM 조회/중간 DataFrame 메모리 최적화
- 필요 시 ECS/Glue/Step Functions 검토

4. `net_sales` 컬럼 재도입
- 데이터 소스 확정 후 UI/집계/엑셀 반영

## 17. 담당자 인수인계 시 가장 먼저 확인할 것 (요약)

1. API Gateway `/bti_revenue/*` 3개 엔드포인트가 응답하는지
2. 조회용 Lambda 핸들러가 `query_handler`인지
3. 배치용 Lambda 핸들러가 `batch_handler`인지
4. S3 `report/materials/meta latest.json` 존재 여부
5. 배치용 Lambda IAM 권한 (특히 S3 PutObject, Athena, Glue)
6. EventBridge 스케줄이 실제 배치용 Lambda를 타깃으로 가리키는지

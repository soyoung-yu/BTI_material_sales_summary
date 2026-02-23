# AWS Lambda Backend Scaffold

이 디렉터리는 다음 구조를 기준으로 준비된 스캐폴딩입니다.

- `lambdas/batch_handler.py`: EventBridge 자정 배치용 Lambda 핸들러 (Athena/SageMaker -> S3 저장 인터페이스 고정)
- `lambdas/query_handler.py`: API Gateway 조회용 Lambda 핸들러 (S3 latest JSON 조회)
- `batch/transformers.py`: 노트북에서 추출한 전처리 유틸 함수(closure/제품명 정규화 등)

## 환경변수 (query lambda)
- `BTI_DATA_BUCKET`
- `BTI_REPORT_LATEST_KEY` (default: `report/latest.json`)
- `BTI_MATERIALS_LATEST_KEY` (default: `materials/latest.json`)
- `BTI_META_LATEST_KEY` (default: `meta/latest.json`)
- `ALLOWED_ORIGIN`

## 환경변수 (batch lambda)
- `BTI_DATA_BUCKET`
- `BTI_REPORT_PREFIX`
- `BTI_MATERIALS_PREFIX`
- `BTI_META_PREFIX`
- `MATERIAL_LIST_S3_PATH` (팀 관리소재 엑셀 S3 경로)
- `ATHENA_DATABASE` (default: `data_mart`)
- `COMP_ID` (default: `1200`)
- `CUSTOMER_COMP_ID` (default: `COMP_ID`)
- `BATCH_LOOKBACK_MONTHS` (default: `24`) 또는 `REPORT_START_DATE`/`REPORT_END_DATE`
- `INCLUDE_NET_SALES` (default: `false`, 현재 UI 미사용)

## 다음 작업
1. SageMaker 호출이 필수라면 `run_batch_pipeline()` 앞/뒤에 SageMaker job/endpoint 연동 추가
2. 실제 소재 엑셀 컬럼명과 `prepare_materials_payload()` 매핑 규칙 검증
3. EventBridge Scheduler(00:00 KST)와 API Gateway 연결

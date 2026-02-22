# Repository Guidelines

## Project Structure & Module Organization
This repository is a static HTML prototype for BTI material-based sales reporting. Core files live at the repo root:

- `index.html`: report generation UI, preview tables, and Excel export flow
- `materials.html`: material management UI (search/filter/add/edit/delete)
- `data.js`: mock datasets (`RAW_SALES_DATA`, `MATERIALS`) and aggregation logic used by both screens
- `sample_df.csv`: sample source data for mock generation
- `service_spec.md`: product requirements and planning notes

There is no `src/`, build pipeline, or backend in this repo yet.

## Build, Test, and Development Commands
No build step is required. Open the HTML files directly in a browser for quick checks.

- `open index.html` (macOS): open the report screen
- `open materials.html` (macOS): open the material management screen
- `python3 -m http.server 8000` (optional): serve locally to avoid browser file restrictions, then visit `http://localhost:8000/index.html`

When changing export logic, verify both on-screen preview and Excel download behavior.

## Coding Style & Naming Conventions
Use plain HTML/CSS/JavaScript with 4-space indentation, matching existing files. Follow current naming patterns:

- `camelCase` for functions/variables (`calculateData`, `renderPreviewTabs`)
- `UPPER_SNAKE_CASE` for constants/data arrays (`RAW_SALES_DATA`, `MATERIALS`)
- descriptive IDs/class names for UI elements (`page-title`, `card-header`)

Keep aggregation logic centralized in `data.js`; avoid duplicating calculations in `index.html`.

## Testing Guidelines
There is no automated test framework configured. Use manual regression checks:

- date range filtering works
- each selected summary tab renders correctly
- Excel download completes and sheet names/columns match the preview
- material CRUD UI interactions behave as expected in `materials.html`

If you add automated tests later, place them in a `tests/` directory and document the run command here.

## Commit & Pull Request Guidelines
Recent commits use short Korean, task-focused messages (examples: `기간 선택 UI 변경`, `샘플 데이터 확장`). Keep commits small and scoped to one change.

For PRs, include:
- a brief summary of user-visible changes
- affected files (for example, `data.js`, `index.html`)
- manual test steps performed
- screenshots/GIFs for UI changes

  ## Language Preference
  - 모든 응답, 작업 설명, 진행 업데이트, 결과 보고는 한국어로 작성한다.
  - CLI 명령어 자체는 원문(영어)으로 유지하되, 설명은 한국어로 한다.
  - 생성되는 문서/주석/커밋 메시지는 특별한 요청이 없으면 한국어로 작성한다.

# Budget Tracker — Test Plan

QA lead: Luke Ford. Last updated November 13, 2026.

## 1. Test approach

| Level | What it covers | How |
| --- | --- | --- |
| Unit | Money, percent, period and report calculations; database models | pytest (`backend/tests/test_money.py`, `test_percent.py`, `test_db.py`, ...) |
| Integration | Each API endpoint with a real SQLite database | pytest + FastAPI TestClient |
| System / acceptance | Whole user journeys through the API: register, log in, add data, read reports | `backend/tests/test_qa_acceptance.py` (TC_01 - TC_32) |
| UI | Frontend build, page load, forms, navigation | Vitest, plus manual and scripted checks in Chrome (TC_33 - TC_46) |
| Security | Missing, invalid and expired tokens; one user reading another's data | pytest (`test_auth_required.py`, TC_08, TC_09, TC_27, TC_28) |
| Regression | Everything above, re-run before every merge | `uv run pytest`, `npm test` |
| Static checks | Lint, formatting, types | ruff, pyright, `tsc` |

## 2. Acceptance criteria (testing to deployment)

1. No Critical or High severity defects are open.
2. 100% of critical test cases pass (registration, login, token checks, data isolation, add/list
   transactions, dashboard loads).
3. At least 95% of all executed test cases pass, and no test case is still blocked.
4. The regression suite passes in full: `uv run pytest`, `npm test`, `npm run build`.
5. `ruff check`, `ruff format --check` and `pyright` report no errors.
6. Every requirement FR1 - FR9 has at least one passing test case.

## 3. Test environment

- Hardware: team laptops (macOS and Linux), no special hardware.
- Backend: Python 3.14, uv, FastAPI, SQLite. Each test gets its own temporary database copy, so
  tests never touch `budgettracker.db`.
- Frontend: Node.js 18 or newer, npm, Vite dev server on port 5173, Google Chrome.
- Tools: pytest 9, FastAPI TestClient, Vitest, Swagger UI (`/docs`), ruff, pyright, GitHub.

## 4. Test data

All test data is made up; no real financial or personal information is used.

- Accounts: `luke@example.com`, `owner@example.com`, `intruder@example.com`, password `TestPass123`.
- Invalid accounts: emails `a@`, `@`, `a b@c`; passwords `short`, `1234567`, eight spaces.
- Expenses: $42.50 Food on 2026-11-05; invalid amounts 0, -5, `abc`, 0.001, 12.345, 100,000,000;
  categories `NotACategory` and empty.
- Income: $1,500 Paycheck on 2026-11-01; invalid amounts 0 and -100.
- Budgets: $500.00 and $750.25 for November 2026; invalid limits 0, -50, 10.999; month 13.
- Tokens: none, `not-a-real-token`, and a real token forced to expire.
- Report data: expenses spread over several categories, months and users (unit test fixtures).

## 5. Test cases per requirement

| Requirement | Test cases | IDs |
| --- | --- | --- |
| FR1 User registration | 5 | TC_01 - TC_05 |
| FR2 Login and token authentication | 4 | TC_06 - TC_09 |
| FR3 Expense management | 7 | TC_10 - TC_16 |
| FR4 Income management | 2 | TC_17 - TC_18 |
| FR5 Monthly budget | 4 | TC_19 - TC_22 |
| FR6 Reports | 4 | TC_23 - TC_26 |
| FR7 Data isolation between users | 2 | TC_27 - TC_28 |
| FR8 Permanent storage | 1 | TC_29 |
| System (health, CORS, API docs) | 3 | TC_30 - TC_32 |
| FR9 Frontend dashboard | 14 | TC_33 - TC_46 |
| **Total** | **46** | |

The developers' 237 backend unit and integration tests and 3 frontend unit tests run alongside
these as the regression suite.

## 6. Resource planning

| Name | Role | Responsibility |
| --- | --- | --- |
| Luke | QA lead | Test plan, acceptance and UI test cases, test report, defect log |
| Rosie | Developer / tester | Unit and integration tests for authentication and transactions; fixes backend defects |
| Daniel | Developer / tester | Unit tests for budgets, reports and the database; fixes backend defects |
| Wany | Developer / tester | Frontend unit tests; fixes frontend defects |
| Tyler | | |

## 7. Defect management

- Defects are logged in Jira and mirrored in `docs/qa/TEST_REPORT.md`, each with steps to
  reproduce, expected and actual results, severity, and the developer it's assigned to.
- Severity: **Critical** (app unusable or data exposed), **High** (a main feature doesn't work),
  **Medium** (wrong behavior with a workaround), **Low** (minor or cosmetic).
- Workflow: New → Open → In Progress → Fixed → Verified → Closed.
- Each backend defect has a test marked `xfail(strict=True)` in `test_qa_acceptance.py`. When the
  fix lands, that test passes, pytest flags it, and QA removes the marker to verify and close.

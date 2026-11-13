# Budget Tracker — Test Report

Run on November 13, 2026 against commit `b1a85a7` by Luke Ford (QA).

## Summary

| | Count |
| --- | --- |
| Test cases planned | 46 |
| Test cases executed | 41 |
| Passed | 27 |
| Failed | 14 |
| Blocked (not executed) | 5 |
| Pass rate of executed cases | 65.9% |

Regression suite (developer-written): 237 of 237 backend tests pass, 3 of 3 frontend unit tests
pass, and ruff, ruff format and pyright report no errors.

**Release decision: not ready for deployment.** One Critical and two High defects are open, and the
pass rate is under the 95% the test plan requires. The backend API on its own is in good shape:
24 of its 32 test cases pass, and all authentication and data-isolation cases pass.

| Area | Planned | Executed | Passed | Failed | Blocked |
| --- | --- | --- | --- | --- | --- |
| Backend API (TC_01 - TC_32) | 32 | 32 | 24 | 8 | 0 |
| Frontend (TC_33 - TC_46) | 14 | 9 | 3 | 6 | 5 |

## Defects

Seven defects found, all open.

| Severity | Open | Closed |
| --- | --- | --- |
| Critical | 1 | 0 |
| High | 2 | 0 |
| Medium | 2 | 0 |
| Low | 2 | 0 |

| ID | Severity | Summary | Failing tests | Assigned | Status |
| --- | --- | --- | --- | --- | --- |
| DEF-01 | Critical | Frontend shows a blank page and doesn't build | TC_34, TC_35 | Wany | Open |
| DEF-02 | High | Transactions are kept in memory, so reports and budget status always show $0 | TC_24, TC_25, TC_26, TC_29 | Rosie, Daniel | Open |
| DEF-03 | High | Frontend has no login and sends no token, so every request gets 401 | TC_38, TC_39 (blocks TC_42 - TC_46) | Wany | Open |
| DEF-04 | Medium | Expenses and income accept unknown categories and amounts that break the money rules | TC_15, TC_16 | Rosie | Open |
| DEF-05 | Low | Registration accepts malformed emails and blank passwords | TC_04, TC_05 | Rosie | Open |
| DEF-06 | Medium | Frontend saves the budget in the browser instead of the backend | TC_40 | Wany | Open |
| DEF-07 | Low | Add forms default to tomorrow's date in the evening | TC_41 | Wany | Open |

### DEF-01: frontend shows a blank page and doesn't build (Critical)

- Steps: unzip `budget-tracker-frontend.zip`, `npm install`, `npm run dev`, open the page.
- Expected: the dashboard. Actual: blank page; console shows `valueText is not defined` from
  `StatCard`. `npm run build` fails with `TS2304: Cannot find name 'valueText'` (App.tsx:232) and
  `TS6133: 'monthLabel' is declared but its value is never read` (App.tsx:17).
- Suggested fix, verified locally: in `src/App.tsx` line 228 add `valueText` to the destructured
  props, `function StatCard({ title, amount, icon, tone, foot, valueText }: {`, and delete the
  unused `monthLabel` on line 17.

### DEF-02: transactions are kept in memory (High)

- Steps: log in, `PUT /budgets/2026/11` with limit 500, `POST /expenses` for 42.50 on 2026-11-05,
  `GET /budgets/2026/11/status`.
- Expected: spent 42.50. Actual: spent 0.00. The summary and spending-by-category reports are
  empty too, and all transactions disappear when the server restarts.
- Cause: `routers/transactions.py` lines 29-30 store data in module-level dicts, while
  `reports.py` reads the `transactions` table. Nothing writes to that table through the API.
- Suggested fix: save expenses and income as `Transaction` rows (already a known remaining task).

### DEF-03: frontend has no login and sends no token (High)

- Steps: with DEF-01 patched, open the dashboard, or add an expense.
- Expected: a login screen, then data loads. Actual: "Authentication required" banner; `GET
  /expenses` and `GET /income` return 401. There's no register or login form, and `src/api.ts`
  line 10 never adds an `Authorization` header.
- Also: `vite.config.ts` only proxies `/expenses`, `/income` and `/health`, so `/register`,
  `/login`, `/me`, `/budgets`, `/reports` and `/categories` won't reach the backend in dev.

### DEF-04: transaction input isn't fully validated (Medium)

- Steps: `POST /expenses` with category `NotACategory`, or amount `0.001` or `100000000`.
- Expected: 422. Actual: 200, saved.
- Cause: `routers/transactions.py` line 14 uses `float` and line 15 a free-text category, instead
  of `MoneyInput` and the ids from `GET /categories` that budgets and reports use.

### DEF-05: weak registration validation (Low)

- Steps: `POST /register` with email `a@` or `@`, or with a password of eight spaces.
- Expected: 422. Actual: 200. `routers/auth.py` line 32 only checks that the email contains `@`.
- Suggested fix: use Pydantic's `EmailStr` and reject whitespace-only passwords.

### DEF-06: budget is saved in the browser only (Medium)

- Steps: with DEF-01 patched, click Edit budget, enter 750, save.
- Expected: `PUT /budgets/2026/11`. Actual: no request is sent; the value goes to `localStorage`
  (App.tsx line 111), so it's lost on another device and the backend's budget status ignores it.
  The frontend README says the backend has no budget endpoint, which is out of date.

### DEF-07: default date is a day ahead in the evening (Low)

- Steps: open Add expense at 8:30 PM Central on November 13.
- Expected: date 11/13. Actual: 11/14. `today()` on App.tsx line 15 uses `toISOString()`, which is
  UTC. The same call for the month picker is fine because it uses local time.

## How to re-run

```sh
cd backend
uv sync
uv run pytest                                   # 290 passed, 14 xfailed
uv run pytest tests/test_qa_acceptance.py -rx   # TC_01 - TC_32, lists each open defect
uv run ruff check && uv run ruff format --check && uv run pyright
```

Frontend: unzip `budget-tracker-frontend.zip`, then `npm install`, `npm test`, `npm run build`.

The 14 `xfailed` results are parametrized runs of the 8 failing backend test cases.

# Budget Tracker — Test Cases

Results from the run on November 13, 2026 (commit `b1a85a7`). TC_01 - TC_32 are automated in
`backend/tests/test_qa_acceptance.py`; TC_33 - TC_46 were run by hand and with a Chrome script
against the frontend in `budget-tracker-frontend.zip`.

| ID | Requirement | Test case | Expected result | Status |
| --- | --- | --- | --- | --- |
| TC_01 | FR1 | Register with a valid email and password, then log in | 200, login succeeds | Pass |
| TC_02 | FR1 | Register an email that's already used (also different case, extra spaces) | 409 | Pass |
| TC_03 | FR1 | Register with a password under 8 characters | 422 | Pass |
| TC_04 | FR1 | Register with a malformed email (`a@`, `@`, `a b@c`) | 422 | **Fail** (DEF-05) |
| TC_05 | FR1 | Register with a password of eight spaces | 422 | **Fail** (DEF-05) |
| TC_06 | FR2 | Log in and call `/me` with the token | 200, own email returned | Pass |
| TC_07 | FR2 | Log in with a wrong password / unknown email | 401, same message for both | Pass |
| TC_08 | FR2 | Call all 13 protected endpoints with no token and with a fake token | 401 every time | Pass |
| TC_09 | FR2 | Use a token after it expires | 401 | Pass |
| TC_10 | FR3 | Add an expense and list expenses | Expense is listed | Pass |
| TC_11 | FR3 | Update an expense's amount and category | List shows new values | Pass |
| TC_12 | FR3 | Delete an expense | List is empty | Pass |
| TC_13 | FR3 | Add an expense with a zero/negative/text amount, bad date, or missing field | 422, nothing saved | Pass |
| TC_14 | FR3 | Update or delete an expense that doesn't exist | 404 | Pass |
| TC_15 | FR3 | Add an expense with an unknown or empty category | 422 | **Fail** (DEF-04) |
| TC_16 | FR3 | Add an expense of 0.001, 12.345 or 100,000,000 | 422 | **Fail** (DEF-04) |
| TC_17 | FR4 | Add income and list income | Income is listed | Pass |
| TC_18 | FR4 | Add income with an invalid amount, date, or no source | 422, nothing saved | Pass |
| TC_19 | FR5 | Set a monthly budget and read it back | Same limit returned | Pass |
| TC_20 | FR5 | Set the same month's budget twice | Second limit replaces the first | Pass |
| TC_21 | FR5 | Set a budget of 0, negative, 10.999, over the maximum, or for month 13 | 422 | Pass |
| TC_22 | FR5 | Read a month with no budget | 404 | Pass |
| TC_23 | FR6 | Read reports for a month with no data | All totals 0.00, no categories | Pass |
| TC_24 | FR6 | Set a $500 budget, add a $42.50 expense, read budget status | Spent 42.50, remaining 457.50, 8.5% | **Fail** (DEF-02) |
| TC_25 | FR6 | Add a Food expense, read spending by category | Food 42.50 | **Fail** (DEF-02) |
| TC_26 | FR6 | Add $1,500 income, read the monthly summary | Total income 1500.00 | **Fail** (DEF-02) |
| TC_27 | FR7 | User B lists, updates and deletes user A's transactions | Empty lists, 404; A's data unchanged | Pass |
| TC_28 | FR7 | User B reads and sets user A's budget month | 404; A's budget unchanged | Pass |
| TC_29 | FR8 | Add an expense and income, check the database | 2 rows in `transactions` | **Fail** (DEF-02) |
| TC_30 | System | Call `/health` without logging in | 200 `running` | Pass |
| TC_31 | System | CORS preflight from the frontend origin and from another site | Allowed / not allowed | Pass |
| TC_32 | System | Open `/docs`; check every endpoint is documented | 200, all paths listed | Pass |
| TC_33 | FR9 | Run the frontend unit tests (`npm test`) | 3 of 3 pass | Pass |
| TC_34 | FR9 | Build the frontend (`npm run build`) | Build succeeds | **Fail** (DEF-01) |
| TC_35 | FR9 | Open the dashboard in Chrome | Dashboard is shown | **Fail** (DEF-01) |
| TC_36 | FR9 | Switch between Overview, Transactions and Reports | Page and breadcrumb change | Pass* |
| TC_37 | FR9 | Enter a negative amount in the Add expense form | Form refuses to submit | Pass* |
| TC_38 | FR9 | Register or log in from the frontend | Login form; data loads after login | **Fail*** (DEF-03) |
| TC_39 | FR9 | Add a $12.50 expense from the frontend | Expense appears in the list | **Fail*** (DEF-03) |
| TC_40 | FR9 | Set a monthly budget from the frontend | Saved to the account on the backend | **Fail*** (DEF-06) |
| TC_41 | FR9 | Open Add expense at 8:30 PM Central | Date defaults to today | **Fail** (DEF-07) |
| TC_42 | FR9 | Edit an expense from the frontend | List shows new values | Blocked (DEF-03) |
| TC_43 | FR9 | Delete an expense from the frontend | Expense is removed | Blocked (DEF-03) |
| TC_44 | FR9 | Add income from the frontend | Income appears in the list | Blocked (DEF-03) |
| TC_45 | FR9 | Compare dashboard totals with the entered data | Totals match | Blocked (DEF-03) |
| TC_46 | FR9 | Compare Reports page category totals with the entered data | Totals match | Blocked (DEF-03) |

\* Run with the one-line DEF-01 fix applied locally, because the page doesn't render without it.

## Sample test script: TC_39, add an expense from the frontend

| | |
| --- | --- |
| Test case ID | TC_39 |
| Test scenario | FR9 / FR3: add an expense |
| Test status | Fail (DEF-03) |
| Test data | Amount 12.50, category Food, description Lunch, date 11/13/2026 |
| Browser | Google Chrome |

| Test step | Expected result |
| --- | --- |
| Start the backend and frontend; open `http://localhost:5173` | Dashboard is shown with no error |
| Click **Add transaction** | "Add an expense" form opens |
| Enter 12.50, choose Food, type Lunch | Fields accept the values |
| Click **Add transaction** in the form | Form closes, "Expense added." is shown |
| Look at Recent transactions | Lunch, Food, -$12.50 is listed and Total expenses is $12.50 |

Actual: the page shows "Authentication required" on load and again on submit, and the form stays
open. The frontend never sends a login token.

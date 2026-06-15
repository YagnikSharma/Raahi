# Raahi Safety Platform - Testing Strategy & Verification Report

This document outlines the testing methodologies, test environment configurations, automated unit-test suites, and manual verification workflows implemented for the **Raahi Public Safety Platform**.

---

## 🧪 Automated Testing Strategy

To ensure database consistency and route security, we implement automated regression tests in `tests/test_app.py`.

### Test Setup Config
- **In-Memory database**: Standard SQLite in-memory databases (`sqlite:///:memory:`) are spun up for each individual test case, ensuring zero side-effects.
- **CSRF Bypass**: Flask WTF-CSRF tokens are disabled during testing to simplify form payload verification.
- **Seeded Objects**: Every test case starts with a seeded test CCTV camera ("Test-CCTV-1") and a registered Administrator user (`admin@example.com` / `admin_password`).

### Automated Test Cases

| File Location | Test Case Name | Goal |
| :--- | :--- | :--- |
| `tests/test_app.py` | `test_database_camera_setup` | Verifies that database migrations and setup seed logic run successfully |
| `tests/test_app.py` | `test_route_safety_planner_endpoint` | Asserts `/api/route-safety` returns three routes with valid distances, safety ratings, and time durations |
| `tests/test_app.py` | `test_voice_emergency_log_saves_to_db` | Sends mock voice SOS inputs and confirms that matching database `Incident` and `Alert` structures are created |
| `tests/test_app.py` | `test_jwt_alerts_unauthenticated` | Asserts `/api/alerts` returns `401 Unauthorized` when requested without Bearer headers |
| `tests/test_app.py` | `test_jwt_alerts_authenticated` | Generates a valid JWT token, attaches to Headers, and confirms `/api/alerts` successfully fetches alerts list |
| `tests/test_app.py` | `test_cctv_analysis_status` | Sign in the test administrator session and verify `/admin/cctv-analysis/status` returns the expected background state |

### Running the Suite
Execute the test runner from the root folder:
```powershell
C:\Users\ayush\AppData\Local\Python\pythoncore-3.14-64\python.exe -m unittest discover -s tests -p "test_*.py"
```

---

## 👁️ Manual E2E Verification Checklist

During manual deployments, verify the following visual features and state validations:

### 1. Light & Dark Themes
- [ ] Theme toggler in the navbar changes the page body class `[data-bs-theme="light/dark"]`.
- [ ] Preferences persist in `localStorage` across page reloads.
- [ ] Transition animations on body background, card containers, and text scale are smooth (`0.5s` morph).
- [ ] Leaflet Map switches tiles from CartoDB Dark Matter to Voyager Voyager style seamlessly.

### 2. Speech recognition (Voice Guardian)
- [ ] Microphone activation spawns the animated SVG wave pulse modal.
- [ ] Speaking keyword phrase "help me" triggers a real-time sliding Toast notice at the top-right corner.
- [ ] Alert details populate on the administrator's dashboard database log.

### 3. Route Safety planner
- [ ] Clicking on the map pins start and destination points.
- [ ] Routes draw polylines colored green (safe), yellow (caution), or red (danger).
- [ ] Sidebar prints safety score metrics, total metrics, and descriptive information cards.

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app.main import app

def test_full_rbac_matrix():
    client = TestClient(app)

    # 1. Unauthenticated requests to protected pages redirect to login
    for page in ["dashboard", "employees", "departments", "scanner", "attendance", "audit-logs", "reports", "settings", "security"]:
        r = client.get(f"/en/{page}", follow_redirects=False)
        assert r.status_code == 302, f"Expected redirect for unauthenticated /{page}, got {r.status_code}"
        assert "/login" in r.headers["location"]
    print("[PASS] Unauthenticated redirects to login.")

    # 2. Check each role against page matrix
    role_creds = {
        "ADMIN": ("admin", "admin123"),
        "HR_MANAGER": ("hr", "hr123"),
        "SECURITY_OFFICER": ("security", "security123"),
        "EMPLOYEE": ("staff", "staff123"),
    }

    expected_page_access = {
        "ADMIN": {"dashboard", "employees", "departments", "scanner", "attendance", "audit-logs", "reports", "settings", "security"},
        "HR_MANAGER": {"dashboard", "employees", "departments", "scanner", "attendance", "reports"},
        "SECURITY_OFFICER": {"dashboard", "scanner", "attendance", "audit-logs"},
        "EMPLOYEE": {"dashboard", "scanner", "attendance"},
    }

    all_pages = ["dashboard", "employees", "departments", "scanner", "attendance", "audit-logs", "reports", "settings", "security"]

    for role_name, (username, password) in role_creds.items():
        c = TestClient(app)
        r_log = c.post("/api/auth/login", data={"username": username, "password": password}, follow_redirects=False)
        assert r_log.status_code == 303, f"Login failed for {username}"

        allowed = expected_page_access[role_name]
        for page in all_pages:
            resp = c.get(f"/en/{page}", follow_redirects=False)
            if page in allowed:
                assert resp.status_code == 200, f"Role {role_name} should have access to {page}, got {resp.status_code}"
            else:
                assert resp.status_code == 403, f"Role {role_name} should be FORBIDDEN (403) from {page}, got {resp.status_code}"
        print(f"[PASS] Page matrix verified for role: {role_name}")

    print("\n>>> ALL RBAC MATRIX TESTS PASSED 100%! <<<")

if __name__ == "__main__":
    test_full_rbac_matrix()


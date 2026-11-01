import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app.main import app

def run_all_tests():
    client_admin = TestClient(app)
    res_login = client_admin.post('/api/auth/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=False)
    assert res_login.status_code == 303

    # 1. Test Navbar and Sidebar avatar rendering
    r = client_admin.get('/en/dashboard')
    assert r.status_code == 200

    from app.database import SessionLocal
    from app.models import User
    _db = SessionLocal()
    _user = _db.query(User).filter_by(username='admin').first()
    expected_avatar = _user.avatar_url or '/static/img/avatar.png'
    _db.close()

    assert expected_avatar in r.text
    print('Avatar URL successfully rendered in dashboard for user 1!')

    count = r.text.count(expected_avatar)
    print('Avatar count in rendered page:', count)
    assert count >= 2, f'Expected at least 2 occurrences (navbar & sidebar), found {count}'

    # 2. Test staff (EMPLOYEE) permissions on APIs
    client_staff = TestClient(app)
    client_staff.post('/api/auth/login', data={'username': 'staff', 'password': 'staff123'}, follow_redirects=False)

    # Staff tries to create department
    r_dept = client_staff.post('/api/departments', data={'code': 'HACK', 'name': 'Hacking Dept'}, follow_redirects=False)
    print('Staff POST /api/departments status:', r_dept.status_code)
    assert r_dept.status_code == 403

    # Staff tries to update system settings
    r_sys = client_staff.post('/api/settings/system', data={'cosine_threshold': '0.5'}, follow_redirects=False)
    print('Staff POST /api/settings/system status:', r_sys.status_code)
    assert r_sys.status_code == 403

    # Staff tries to export backup
    r_bk = client_staff.get('/api/settings/backup', follow_redirects=False)
    print('Staff GET /api/settings/backup status:', r_bk.status_code)
    assert r_bk.status_code == 403

    # Staff sidebar should NOT contain links to /security, /departments, /employees, /audit-logs, /reports
    r_staff_dash = client_staff.get('/en/dashboard')
    assert 'href="/en/security"' not in r_staff_dash.text
    assert 'href="/en/departments"' not in r_staff_dash.text
    assert 'href="/en/employees"' not in r_staff_dash.text
    assert 'href="/en/audit-logs"' not in r_staff_dash.text
    assert 'href="/en/reports"' not in r_staff_dash.text
    print('Staff sidebar cleanly hides forbidden navigation links!')

    # 3. Test logout flow
    r_logout = client_admin.get('/en/logout', follow_redirects=False)
    print('Logout status:', r_logout.status_code, r_logout.headers.get('location'))
    assert r_logout.status_code == 302
    assert 'message=' in r_logout.headers.get('location')

    # Try accessing dashboard after logout
    r_dash_after = client_admin.get('/en/dashboard', follow_redirects=False)
    print('Dashboard access after logout:', r_dash_after.status_code, r_dash_after.headers.get('location'))
    assert r_dash_after.status_code == 302
    assert '/en/login' in r_dash_after.headers.get('location')

    print('\n>>> ALL TEST CASES PASSED 100% SUCCESFULLY! <<<')

if __name__ == '__main__':
    run_all_tests()

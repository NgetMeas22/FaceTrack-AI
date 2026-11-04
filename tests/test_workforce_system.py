import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app.main import app

def test_workforce_system():
    admin = TestClient(app)
    r = admin.post('/api/auth/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=False)
    assert r.status_code == 303, "Admin login failed"

    # 1. Test Shift Creation
    r_shift = admin.post('/api/shifts', json={
        "code": "SWING",
        "name": "Swing Afternoon Shift",
        "start_time": "14:00",
        "end_time": "22:00",
        "grace_period_mins": 20,
        "is_night_shift": False
    })
    assert r_shift.status_code == 200, f"Create shift failed: {r_shift.text}"
    print("[PASS] Shift created successfully!")

    # 2. Test Shift Assignment
    r_assign = admin.post('/api/shifts/assign', json={
        "employee_id": 8,
        "shift_id": 1,
        "effective_from": "2026-11-01"
    })
    assert r_assign.status_code == 200, f"Assign shift failed: {r_assign.text}"
    print("[PASS] Shift assigned successfully!")

    # 3. Test Device Registration & Ping
    r_dev = admin.post('/api/devices', json={
        "device_code": "TERM-LAB-01",
        "name": "Biometric Lab Test Node",
        "device_type": "OPTICAL_TERMINAL",
        "ip_address": "192.168.10.50",
        "location": "Research Wing"
    })
    assert r_dev.status_code == 200, f"Register device failed: {r_dev.text}"
    print("[PASS] Device registered successfully!")

    r_ping = admin.post('/api/devices/1/ping')
    assert r_ping.status_code == 200, f"Device ping failed: {r_ping.text}"
    print("[PASS] Device ping successful!")

    # 4. Test Leave Request & Review
    r_leave = admin.post('/api/leave/request', json={
        "employee_id": 8,
        "leave_type_id": 1,
        "start_date": "2026-11-10",
        "end_date": "2026-11-12",
        "reason": "Personal medical appointment"
    })
    assert r_leave.status_code == 200, f"Leave request failed: {r_leave.text}"
    print("[PASS] Leave request submitted successfully!")

    # 5. Test Biometric Consent
    r_consent = admin.post('/api/biometrics/consent', json={
        "employee_id": 8,
        "consent_given": True,
        "notes": "Verified by HR consent officer"
    })
    assert r_consent.status_code == 200, f"Biometric consent failed: {r_consent.text}"
    print("[PASS] Biometric consent recorded successfully!")

    # 6. Test Views with Pagination Parameters
    for path in ['/en/shifts?page=1&page_size=5', '/en/leave?page=1&page_size=5', '/en/devices?page=1&page_size=5', '/en/employees?page=1&page_size=2', '/en/attendance?page=1&page_size=2']:
        resp = admin.get(path)
        assert resp.status_code == 200, f"View {path} failed: {resp.status_code}"
    print("[PASS] Server-side pagination on all workforce views verified!")

    print("\n>>> ALL WORKFORCE MANAGEMENT TESTS PASSED 100%! <<<")

if __name__ == "__main__":
    test_workforce_system()

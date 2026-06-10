from jedify_lens.tools import registration


def test_validate_callback_success():
    code, err = registration.validate_callback({"code": "c", "state": "RIGHT"}, "RIGHT")
    assert code == "c"
    assert err is None


def test_validate_callback_state_mismatch():
    code, err = registration.validate_callback({"code": "c", "state": "WRONG"}, "RIGHT")
    assert code is None
    assert err["success"] is False
    assert "verif" in err["action"].lower()


def test_validate_callback_provider_error():
    code, err = registration.validate_callback({"error": "access_denied"}, "RIGHT")
    assert code is None
    assert err["success"] is False


def test_validate_callback_missing_code():
    code, err = registration.validate_callback({"state": "RIGHT"}, "RIGHT")
    assert code is None
    assert err["success"] is False
    assert "code" in err["action"].lower()

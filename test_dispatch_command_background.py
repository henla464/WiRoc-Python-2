"""Self-check for BackgroundTasks.DispatchCommandBackground. Run on a device/venv with the
full WiRoc dependency set (this repo's heavy imports require it, same as BackgroundTasks.py itself):
    python3 test_dispatch_command_background.py
"""
from unittest.mock import patch, Mock

from BackgroundTasks import BackgroundTasks

SELF_BT = "AA:AA:AA:AA:AA:AA"
SIBLING_BT = "BB:BB:BB:BB:BB:BB"
SIBLING_IP = "192.168.1.50"


def fake_response(status_code, json_data=None, text=""):
    resp = Mock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text
    return resp


def test_self_targeted_skips_verification():
    command = {"targetBtAddress": SELF_BT, "path": "/api/status/", "params": {}}
    with patch("BackgroundTasks.requests.get", return_value=fake_response(200, text="ok")) as mock_get:
        status, result = BackgroundTasks.DispatchCommandBackground(command, SELF_BT)
    assert status == 200 and result == "ok"
    mock_get.assert_called_once_with(url="http://localhost:5000/api/status/", params={}, timeout=10)


def test_relay_dispatches_after_matching_identify():
    command = {"targetBtAddress": SIBLING_BT, "targetLocalIPAddress": SIBLING_IP,
               "path": "/api/status/", "params": {}}
    identify_resp = fake_response(200, {"Value": {"btAddress": SIBLING_BT}})
    real_resp = fake_response(200, text="sibling-ok")
    with patch("BackgroundTasks.requests.get", side_effect=[identify_resp, real_resp]):
        status, result = BackgroundTasks.DispatchCommandBackground(command, SELF_BT)
    assert (status, result) == (200, "sibling-ok")


def test_relay_mismatch_short_circuits():
    command = {"targetBtAddress": SIBLING_BT, "targetLocalIPAddress": SIBLING_IP,
               "path": "/api/power/restart/", "params": {}}
    wrong_identify_resp = fake_response(200, {"Value": {"btAddress": "WRONG:ADDRESS"}})
    with patch("BackgroundTasks.requests.get", return_value=wrong_identify_resp) as mock_get:
        status, result = BackgroundTasks.DispatchCommandBackground(command, SELF_BT)
    assert status == -1 and "mismatch" in result
    assert mock_get.call_count == 1  # never attempted the real (restart) command


def test_relay_unreachable_does_not_raise():
    command = {"targetBtAddress": SIBLING_BT, "targetLocalIPAddress": SIBLING_IP,
               "path": "/api/status/", "params": {}}
    with patch("BackgroundTasks.requests.get", side_effect=ConnectionError("no route")):
        status, result = BackgroundTasks.DispatchCommandBackground(command, SELF_BT)
    assert status == -1 and "no route" in result


def test_path_without_leading_slash_is_rejected_before_any_request():
    # "http://localhost:5000" + "@evil.com/foo" parses evil.com as the host (urlsplit-confirmed) -
    # must be rejected before building the URL, not just before dispatching it.
    command = {"targetBtAddress": SELF_BT, "path": "@evil.com/foo", "params": {}}
    with patch("BackgroundTasks.requests.get") as mock_get:
        status, result = BackgroundTasks.DispatchCommandBackground(command, SELF_BT)
    assert status == -1 and "invalid command path" in result
    mock_get.assert_not_called()


def test_path_template_placeholders_are_substituted_from_params():
    command = {"targetBtAddress": SELF_BT, "path": "/api/setting/<key>/<value>/",
               "params": {"key": "LongPollCommandsEnabled", "value": "1"}}
    with patch("BackgroundTasks.requests.get", return_value=fake_response(200, text="ok")) as mock_get:
        status, result = BackgroundTasks.DispatchCommandBackground(command, SELF_BT)
    assert status == 200
    mock_get.assert_called_once_with(
        url="http://localhost:5000/api/setting/LongPollCommandsEnabled/1/", params={}, timeout=10)


def test_leftover_params_become_query_string_for_plain_paths():
    command = {"targetBtAddress": SELF_BT, "path": "/api/roc/",
               "params": {"lastId": "5", "date": "2026-11-19"}}
    with patch("BackgroundTasks.requests.get", return_value=fake_response(200, text="ok")) as mock_get:
        BackgroundTasks.DispatchCommandBackground(command, SELF_BT)
    mock_get.assert_called_once_with(
        url="http://localhost:5000/api/roc/", params={"lastId": "5", "date": "2026-11-19"}, timeout=10)


def test_missing_placeholder_value_is_reported_not_raised():
    command = {"targetBtAddress": SELF_BT, "path": "/api/setting/<key>/<value>/", "params": {"key": "X"}}
    with patch("BackgroundTasks.requests.get") as mock_get:
        status, result = BackgroundTasks.DispatchCommandBackground(command, SELF_BT)
    assert status == -1 and "missing param" in result
    mock_get.assert_not_called()


def test_blocked_command_is_never_dispatched():
    for blockedPath in ("/api/dropalltables/", "/api/deletepunches/"):
        command = {"targetBtAddress": SELF_BT, "path": blockedPath, "params": {}}
        with patch("BackgroundTasks.requests.get") as mock_get:
            status, result = BackgroundTasks.DispatchCommandBackground(command, SELF_BT)
        assert status == -1 and "not allowed" in result, blockedPath
        mock_get.assert_not_called()


def test_malicious_param_cannot_inject_host_after_substitution():
    command = {"targetBtAddress": SELF_BT, "path": "/api/setting/<key>/<value>/",
               "params": {"key": "@evil.com", "value": "1"}}
    with patch("BackgroundTasks.requests.get") as mock_get:
        status, result = BackgroundTasks.DispatchCommandBackground(command, SELF_BT)
    assert status == -1 and "invalid command path" in result
    mock_get.assert_not_called()


def test_do_pending_commands_returns_true_when_commands_present():
    pending_resp = fake_response(200, {"commands": [
        {"commandId": 1, "targetBtAddress": SELF_BT, "path": "/api/status/", "params": {}}
    ]})
    dispatch_resp = fake_response(200, text="ok")
    with patch("BackgroundTasks.requests.get", side_effect=[pending_resp, dispatch_resp]), \
         patch("BackgroundTasks.requests.post", return_value=fake_response(200)) as mock_post:
        result = BackgroundTasks.DoPendingCommandsBackground("https://monitor", "key", SELF_BT)
    assert result is True  # caller re-polls immediately when this is True
    mock_post.assert_called_once()  # CommandResult still posted for the processed command


def test_do_pending_commands_returns_false_when_empty():
    with patch("BackgroundTasks.requests.get", return_value=fake_response(200, {"commands": []})), \
         patch("BackgroundTasks.requests.post") as mock_post:
        result = BackgroundTasks.DoPendingCommandsBackground("https://monitor", "key", SELF_BT)
    assert result is False  # caller falls back to the normal 15s cadence
    mock_post.assert_not_called()


def test_do_pending_commands_returns_false_on_bad_status():
    with patch("BackgroundTasks.requests.get", return_value=fake_response(503)):
        result = BackgroundTasks.DoPendingCommandsBackground("https://monitor", "key", SELF_BT)
    assert result is False


def test_do_pending_commands_returns_false_on_exception():
    with patch("BackgroundTasks.requests.get", side_effect=ConnectionError("down")):
        result = BackgroundTasks.DoPendingCommandsBackground("https://monitor", "key", SELF_BT)
    assert result is False


if __name__ == "__main__":
    test_self_targeted_skips_verification()
    test_relay_dispatches_after_matching_identify()
    test_relay_mismatch_short_circuits()
    test_relay_unreachable_does_not_raise()
    test_path_without_leading_slash_is_rejected_before_any_request()
    test_path_template_placeholders_are_substituted_from_params()
    test_leftover_params_become_query_string_for_plain_paths()
    test_missing_placeholder_value_is_reported_not_raised()
    test_blocked_command_is_never_dispatched()
    test_malicious_param_cannot_inject_host_after_substitution()
    test_do_pending_commands_returns_true_when_commands_present()
    test_do_pending_commands_returns_false_when_empty()
    test_do_pending_commands_returns_false_on_bad_status()
    test_do_pending_commands_returns_false_on_exception()
    print("All DispatchCommandBackground checks passed.")

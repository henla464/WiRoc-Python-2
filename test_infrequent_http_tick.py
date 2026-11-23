"""Self-check for the infrequent-HTTP process waking early on RequestInfrequentHTTPTick()
(mesh snapshot uploads no longer wait out the 40 s inter-tick sleep).
Run on a device/venv with the full WiRoc dependency set:
    python3 test_infrequent_http_tick.py
Everything below HTTP is stubbed; no database, hardware or network is touched.
"""
import threading
import time
from multiprocessing import Queue

from BackgroundTasks import BackgroundTasks
from settings.settings import SettingsClass


def test_wait_wakes_on_command():
    q = Queue()
    BackgroundTasks.InfrequentHTTPQueue = q
    BackgroundTasks.RequestInfrequentHTTPTick()
    assert BackgroundTasks._WaitForQueuedCommand(q, 5) == "START"

    start = time.monotonic()
    assert BackgroundTasks._WaitForQueuedCommand(Queue(), 0.2) is None
    assert time.monotonic() - start >= 0.2


def test_loop_tick_runs_right_after_nudge():
    ticks = []
    stubs = {
        "InvalidateCachesIfSettingsUpdated": staticmethod(lambda: None),
        "GetBTAddress": staticmethod(lambda: "AA:BB"),
        "GetWebServerUrl": staticmethod(lambda: "http://monitor.invalid"),
        "GetAPIKey": staticmethod(lambda: "key"),
        "GetWiRocDeviceName": staticmethod(lambda: None),
    }
    saved = {name: SettingsClass.__dict__[name] for name in stubs}
    for name, stub in stubs.items():
        setattr(SettingsClass, name, stub)
    savedMesh = BackgroundTasks.SendMeshSnapshotBackground
    BackgroundTasks.SendMeshSnapshotBackground = staticmethod(
        lambda url, key, bt, state: (ticks.append(time.monotonic()), state)[1])
    BackgroundTasks.UpdateBatteryIsLowReceivedBackground = staticmethod(lambda *a: True)
    BackgroundTasks.UpdateBatteryIsLowBackground = staticmethod(lambda *a: False)
    BackgroundTasks.SendSetConnectedToInternetBackground = staticmethod(lambda *a: None)
    BackgroundTasks.AddDeviceBackground = staticmethod(lambda *a: None)
    BackgroundTasks.PostAvailableCommandsBackground = staticmethod(lambda *a: True)
    try:
        q = Queue()
        thread = threading.Thread(
            target=BackgroundTasks.DoInfrequentHTTPTasksBackground, args=(q, False, False), daemon=True)
        thread.start()
        time.sleep(0.3)
        assert len(ticks) == 1, "expected exactly the startup tick before any nudge, and no busy loop"
        nudgeAt = time.monotonic()
        BackgroundTasks.InfrequentHTTPQueue = q
        BackgroundTasks.RequestInfrequentHTTPTick()
        time.sleep(0.3)
        assert len(ticks) == 2 and ticks[1] - nudgeAt < 0.3, "upload tick did not run within 0.3 s of the nudge"
        q.put("EXIT", False)
        thread.join(2)
        assert not thread.is_alive(), "loop did not exit on EXIT"
    finally:
        for name, value in saved.items():
            setattr(SettingsClass, name, value)
        BackgroundTasks.SendMeshSnapshotBackground = savedMesh


def main():
    test_wait_wakes_on_command()
    test_loop_tick_runs_right_after_nudge()
    print("all infrequent HTTP tick checks passed")


if __name__ == '__main__':
    main()

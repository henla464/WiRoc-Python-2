"""Self-check for LORA_IRQ meaning "host message OR topology map available":
an asserted IRQ polls the mesh snapshot despite the 60 s gate, an idle one keeps it.
Hardware, settings storage, serial and background uploads are stubbed.
Run with the device venv: python3 test_mesh_snapshot_irq_poll.py
"""
import sys
import time
import types
from contextlib import contextmanager
from types import SimpleNamespace

try:
    import creedsolo  # noqa: F401  (device-only dependency)
except ModuleNotFoundError:
    stub = types.ModuleType("creedsolo")

    class ReedSolomonError(Exception):
        pass

    class RSCodec:
        def __init__(self, *args, **kwargs):
            pass

    stub.ReedSolomonError = ReedSolomonError
    stub.RSCodec = RSCodec
    sys.modules["creedsolo"] = stub

import inputadapters.receiveloraadapter as rec
from BackgroundTasks import BackgroundTasks
from settings.settings import SettingsClass

calls = []
promoted = []
ticks = []


class FakeLoraRadio:
    def GetMeshState(self):
        calls.append("state")
        return {"isroot": 1, "hops": 0}

    def GetMeshTopology(self):
        calls.append("topo")
        return [{"addr": 1}]


@contextmanager
def stubbed():
    saved = {name: SettingsClass.__dict__[name] for name in
             ("GetMeshEnabled", "GetBTAddress", "SetMeshHopCount", "SetSetting",
              "GetMeshStandbyRoot", "GetMeshPromoted", "SetMeshPromoted")}
    SettingsClass.GetMeshEnabled = staticmethod(lambda: True)
    SettingsClass.GetBTAddress = staticmethod(lambda: "AA:BB")
    SettingsClass.SetMeshHopCount = staticmethod(lambda *a: None)
    SettingsClass.SetSetting = staticmethod(lambda *a: None)
    SettingsClass.GetMeshStandbyRoot = staticmethod(lambda: True)
    SettingsClass.GetMeshPromoted = staticmethod(lambda: False)
    SettingsClass.SetMeshPromoted = staticmethod(lambda value: promoted.append(value))
    savedTick = BackgroundTasks.__dict__["RequestInfrequentHTTPTick"]
    BackgroundTasks.RequestInfrequentHTTPTick = staticmethod(lambda: ticks.append(1))
    try:
        yield
    finally:
        for name, value in saved.items():
            setattr(SettingsClass, name, value)
        BackgroundTasks.RequestInfrequentHTTPTick = savedTick


def makeAdapter(irq, secondsSinceLastPoll):
    return SimpleNamespace(
        hardwareAbstraction=SimpleNamespace(GetLORAIRQValue=lambda: irq),
        loraRadio=FakeLoraRadio(),
        lastMeshSnapshotTime=time.monotonic() - secondsSinceLastPoll,
        lastMeshStatePollTime=0.0,
        lastStoredTopology=None)


def main():
    with stubbed():
        # IRQ asserted = something to fetch: poll now even though only 10 s passed.
        calls.clear()
        adapter = makeAdapter(True, 10.0)
        rec.ReceiveLoraAdapter.UpdateMeshSnapshot(adapter, False)
        assert calls == ["state", "topo"], calls
        assert adapter.lastMeshSnapshotTime > time.monotonic() - 60.0
        assert ticks, "changed topology should request an upload tick"

        # A pending message always takes priority over the topo poll.
        calls.clear()
        rec.ReceiveLoraAdapter.UpdateMeshSnapshot(makeAdapter(True, 10.0), True)
        assert calls == [], calls

        # IRQ low: normal 60 s cadence.
        calls.clear()
        rec.ReceiveLoraAdapter.UpdateMeshSnapshot(makeAdapter(False, 10.0), False)
        assert calls == [], calls
        rec.ReceiveLoraAdapter.UpdateMeshSnapshot(makeAdapter(False, 70.0), False)
        assert calls == ["state", "topo"], calls

        # The 2 s floor still rate-limits a stuck IRQ.
        calls.clear()
        rec.ReceiveLoraAdapter.UpdateMeshSnapshot(makeAdapter(True, 1.0), False)
        assert calls == [], calls

        # Promoted-state polling is no longer blocked by an asserted IRQ either.
        promoted.clear()
        adapter = makeAdapter(True, 10.0)
        rec.ReceiveLoraAdapter.UpdateMeshPromotedState(adapter, False)
        assert promoted == [True], promoted

    print("all mesh snapshot IRQ poll checks passed")


if __name__ == '__main__':
    main()

"""Self-check for the ATC+MESHSTATE / ATC+MESHTOPO parsers across the old and new
firmware wire formats (alloc ver / age ms inserted positionally).
Run with the device venv: python3 test_mesh_at_parsers.py
"""
import sys
import types

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

from loraradio.LoraRadioRAK3172 import LoraRadioRAK3172

STATE = "ATC+MESHSTATE="
TOPO = "ATC+MESHTOPO="
BASE_STATE = "1:0:3:0:2:4"              # enabled..alloc
TAIL = ":1:9:1:2:1:2:2:1"               # parent,hops,cost,neighbours,epoch,overhead,ackms,standby
COUNTERS = ":10:11:12:13:14:15:7"       # tx_ok..last_type


def main():
    # Old firmware: no allocver.
    value = LoraRadioRAK3172.ParseMeshStateResponse(STATE + BASE_STATE + TAIL)
    assert "allocver" not in value and value["parent"] == 1 and value["standby"] == 1, value

    # New firmware: allocver between alloc and parent, with and without counters.
    value = LoraRadioRAK3172.ParseMeshStateResponse(STATE + BASE_STATE + ":7" + TAIL)
    assert value["allocver"] == 7 and value["parent"] == 1 and value["standby"] == 1, value
    value = LoraRadioRAK3172.ParseMeshStateResponse(STATE + BASE_STATE + ":7" + TAIL + COUNTERS)
    assert value["allocver"] == 7 and value["adopt"] == 15 and value["last_type"] == 7, value

    # Topology, old row shapes (with and without neighbours).
    rows = LoraRadioRAK3172.ParseMeshTopologyResponse(TOPO + "3:1:001122334455:1=5,2=9|4:3:665544332211")
    assert rows[0] == {"addr": 3, "parent": 1, "deviceId": "001122334455",
                       "neighbours": [{"addr": 1, "cost": 5}, {"addr": 2, "cost": 9}]}, rows[0]
    assert rows[1]["neighbours"] == [] and "ageMs" not in rows[1], rows[1]

    # Topology, new row shapes (age between id and neighbour list; never-reported sentinel).
    rows = LoraRadioRAK3172.ParseMeshTopologyResponse(
        TOPO + "3:1:001122334455:1200:1=5|4:3:665544332211:4294967295")
    assert rows[0]["ageMs"] == 1200 and rows[0]["neighbours"] == [{"addr": 1, "cost": 5}], rows[0]
    assert rows[1]["ageMs"] == 4294967295 and rows[1]["neighbours"] == [], rows[1]

    print("all mesh AT parser checks passed")


if __name__ == '__main__':
    main()

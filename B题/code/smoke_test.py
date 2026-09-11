#!/usr/bin/env python3
"""端到端冒烟测试：本地起 mock 模拟器，用 RobotClient 完成一次完整流程并核对计时。

运行: python smoke_test.py
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mock_simulator as ms
from robot_client import RobotClient


class Args:
    pass


def free_world(seed=7, count=3, mode="q3"):
    args = Args()
    args.port = 0
    args.seed = seed
    args.count = count
    args.mode = mode
    args.scenario = None
    args.robot_id = "TESTTEAM"
    args.log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
    args.quiet = True
    return ms.build_world(args, robot_id="TESTTEAM")


def main():
    world = free_world()
    server = ms.make_server(0, world)
    port = server.server_address[1]
    client = RobotClient("http://127.0.0.1:%d" % port, "TESTTEAM",
                         log_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs", "smoke_client.jsonl"))
    ok = True

    status, response = client.enter()
    assert status == 200 and response["accepted"] is True, response
    print("enter ok, remaining_real_duration_s =", response["remaining_real_duration_s"])

    src = world.scenario.sources[0]
    ox, oy = 0.0, 0.0
    px, py = ox + 400.0, oy + 300.0
    status, response = client.measure(px, py, src["channel"])
    print("measure#1", response)
    expect_move = (px ** 2 + py ** 2) ** 0.5 / 5.0
    expect_switch = 1.0 if src["channel"] != 1 else 0.0
    expect = expect_move + expect_switch + 5.0
    if abs(client.virtual_time - expect) > 1e-6:
        ok = False
        print("FAIL virtual_time expected %.6f got %.6f" % (expect, client.virtual_time))

    status, response = client.measure(px, py, src["channel"])
    expect += 5.0
    if abs(client.virtual_time - expect) > 1e-6:
        ok = False
        print("FAIL repeat measure time expected %.6f got %.6f" % (expect, client.virtual_time))

    if response.get("measure_result") == "direction":
        svd = response["svd_deg"]
        real = ms.ang_norm(ms.math.degrees(ms.math.atan2(src["y"] - py, src["x"] - px)))
        err = ms.ang_diff(svd, real)
        print("svd=%.2f true=%.2f err=%.2f" % (svd, real, err))
        if err > ms.SV_ERROR_DEG + 1e-9:
            ok = False
            print("FAIL svd error out of range")

    tx, ty = src["x"] + 10.0, src["y"] + 10.0
    status, response = client.clear(tx, ty, src["channel"])
    print("clear#1", response)
    if response.get("clear_result") != "success":
        ok = False
        print("FAIL expected clear success")
    if client.channel != src["channel"]:
        ok = False
        print("FAIL clear must not change machine channel")

    status, response = client.clear(tx, ty, src["channel"])
    if response.get("clear_result") != "no_target_in_range":
        ok = False
        print("FAIL repeat clear should miss")

    status, response = client.exit()
    print("exit", response)
    truth = world.scenario.truth()
    print("truth:", json.dumps({k: truth[k] for k in ("total", "cleared", "omni", "dir")}))
    client.close_log("smoke")
    server.shutdown()
    print("SMOKE", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

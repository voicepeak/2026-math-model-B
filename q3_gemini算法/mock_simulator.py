#!/usr/bin/env python3
"""本地协议模拟器（开发用）。

按《模拟器通信接口说明及编程指南》实现 /enter /measure /clear /exit 四条指令的
HTTP+JSON 协议与虚拟计时规则，用于在没有 Windows 真机模拟器时开发和自测机器狗程序。

用法:
    python mock_simulator.py --port 2026 --seed 42 --mode q3
    python mock_simulator.py --scenario scenario.json --port 2027
"""
import argparse
import json
import math
import os
import random
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MAX_BODY = 65536
MAX_COORD = 2000000.0
ARENA_RADIUS = 1800.0
CHANNEL_MIN, CHANNEL_MAX = 1, 20
MOVE_SPEED = 5.0
MEASURE_TIME = 5.0
SWITCH_TIME = 1.0
CLEAR_FOUND_TIME = 5.0
CLEAR_MISS_TIME = 3.0
NEAR_DIST = 5.0
CLEAR_DIST = 20.0
MAX_REAL_S = 1200.0
MAX_VIRTUAL_S = 360000.0
SV_ERROR_DEG = 1.0
EXIT_USER = "user_exit"

KNOWN_PATHS = ("/enter", "/measure", "/clear", "/exit")


def ang_norm(deg):
    return deg % 360.0


def ang_diff(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


class Scenario:
    """案例数据：频道、位置、有效接收半径、类型、定向方向。"""

    def __init__(self, seed=None, count=None, mode="q3", fixed=None):
        if fixed is not None:
            self.sources = [dict(s) for s in fixed]
            return
        rng = random.Random(seed)
        n = count if count is not None else rng.randint(10, 16)
        channels = rng.sample(range(CHANNEL_MIN, CHANNEL_MAX + 1), n)
        sources = []
        for ch in channels:
            r = math.sqrt(rng.random()) * ARENA_RADIUS
            t = rng.uniform(0.0, 2.0 * math.pi)
            kind = "omni"
            direction = None
            if mode == "q4" and rng.random() < 0.4:
                kind = "dir"
                direction = round(rng.uniform(0.0, 360.0), 3)
            sources.append({
                "channel": ch,
                "x": round(r * math.cos(t), 3),
                "y": round(r * math.sin(t), 3),
                "radius": round(rng.uniform(1000.0, 1500.0), 3),
                "type": kind,
                "direction": direction,
                "cleared": False,
            })
        self.sources = sources

    def truth(self):
        return {
            "total": len(self.sources),
            "omni": sum(1 for s in self.sources if s["type"] == "omni"),
            "dir": sum(1 for s in self.sources if s["type"] == "dir"),
            "cleared": sum(1 for s in self.sources if s["cleared"]),
            "sources": [{k: s[k] for k in ("channel", "x", "y", "radius", "type", "direction", "cleared")} for s in self.sources],
        }


class World:
    def __init__(self, scenario, log_path, quiet=False, rng_seed=0):
        self.scenario = scenario
        self.log_path = log_path
        self.quiet = quiet
        self.lock = threading.RLock()
        self.rng = random.Random(rng_seed)
        self.reset()

    def reset(self):
        self.entered = False
        self.exited = False
        self.position = (0.0, 0.0)
        self.channel = 1
        self.virtual_time = 0.0
        self.request_cache = {}
        self.sv_error = {}
        self.real_enter_monotonic = None
        self.request_count = 0
        for s in self.scenario.sources:
            s["cleared"] = False

    def log(self, event):
        event = dict(event)
        event["log_ms"] = int(time.time() * 1000)
        line = json.dumps(event, ensure_ascii=False)
        with self.lock:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        if not self.quiet and event.get("event") != "replay":
            print(line, flush=True)

    def _svd_error(self, channel, x, y):
        key = (channel, round(x, 6), round(y, 6))
        if key not in self.sv_error:
            self.sv_error[key] = self.rng.uniform(-SV_ERROR_DEG, SV_ERROR_DEG)
        return self.sv_error[key]

    def _bearing(self, sx, sy, px, py):
        return ang_norm(math.degrees(math.atan2(sy - py, sx - px)))

    def _in_coverage(self, src, px, py):
        if src["type"] == "omni":
            return True
        bearing_from_src = ang_norm(math.degrees(math.atan2(py - src["y"], px - src["x"])))
        return ang_diff(bearing_from_src, src["direction"]) <= 90.0

    def _find_source(self, channel):
        for s in self.scenario.sources:
            if s["channel"] == channel and not s["cleared"]:
                return s
        return None

    def _advance(self, x, y):
        dx = x - self.position[0]
        dy = y - self.position[1]
        return math.hypot(dx, dy) / MOVE_SPEED

    def measure(self, x, y, channel):
        move = self._advance(x, y)
        switch = SWITCH_TIME if channel != self.channel else 0.0
        self.virtual_time += move + switch + MEASURE_TIME
        self.position = (x, y)
        self.channel = channel
        src = self._find_source(channel)
        result = {"accepted": True, "virtual_time_s": round(self.virtual_time, 6)}
        if src is None:
            result["measure_result"] = "no_signal"
            return result
        dist = math.hypot(x - src["x"], y - src["y"])
        if not self._in_coverage(src, x, y):
            result["measure_result"] = "no_signal"
            return result
        if dist <= NEAR_DIST:
            result["measure_result"] = "near"
            return result
        if dist > src["radius"]:
            result["measure_result"] = "no_signal"
            return result
        truth = self._bearing(src["x"], src["y"], x, y)
        svd = ang_norm(truth + self._svd_error(channel, x, y))
        result["measure_result"] = "direction"
        result["svd_deg"] = round(svd, 2)
        return result

    def clear(self, x, y, channel):
        move = self._advance(x, y)
        self.position = (x, y)
        src = self._find_source(channel)
        hit = src is not None and math.hypot(x - src["x"], y - src["y"]) <= CLEAR_DIST
        self.virtual_time += move + (CLEAR_FOUND_TIME if hit else CLEAR_MISS_TIME)
        result = {"accepted": True, "virtual_time_s": round(self.virtual_time, 6)}
        if hit:
            src["cleared"] = True
            result["clear_result"] = "success"
        else:
            result["clear_result"] = "no_target_in_range"
        return result


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    world = None

    def log_message(self, fmt, *args):
        pass

    def _send(self, status, obj):
        body = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _reject(self, status, err_msg, request_id=None):
        now_ms = int(time.time() * 1000)
        self._send(status, {
            "accepted": False,
            "real_timestamp_ms": now_ms,
            "virtual_time_s": 0,
            "http_status": status,
            "err_msg": err_msg,
        })
        self.world.log({"event": "reject", "http_status": status, "err_msg": err_msg, "request_id": request_id})

    def do_GET(self):
        self._reject(405, "method not allowed")

    def do_PUT(self):
        self._reject(405, "method not allowed")

    def do_DELETE(self):
        self._reject(405, "method not allowed")

    def do_POST(self):
        world = self.world
        path = self.path
        if path not in KNOWN_PATHS:
            self._reject(404, "unknown path")
            return
        ctype = self.headers.get("Content-Type", "")
        parts = [p.strip().lower() for p in ctype.split(";") if p.strip()]
        if not parts or parts[0] != "application/json" or any(p != "charset=utf-8" for p in parts[1:]):
            self._reject(415, "unsupported content type")
            return
        cenc = self.headers.get("Content-Encoding", "identity").strip().lower() or "identity"
        if cenc != "identity":
            self._reject(415, "unsupported content encoding")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._reject(400, "bad content length")
            return
        if length > MAX_BODY:
            self._reject(413, "body too large")
            return
        raw = self.rfile.read(length)
        try:
            text = raw.decode("utf-8")
            if text.startswith("\ufeff"):
                raise ValueError("BOM not allowed")
        except UnicodeDecodeError:
            self._reject(400, "body must be utf-8")
            return
        dup = []

        def pairs_hook(pairs):
            seen = set()
            for k, _ in pairs:
                if k in seen:
                    dup.append(k)
                seen.add(k)
            return dict(pairs)

        try:
            body = json.loads(text, object_pairs_hook=pairs_hook)
        except ValueError:
            self._reject(400, "invalid json")
            return
        if dup:
            self._reject(400, "duplicate keys: %s" % ",".join(sorted(dup)))
            return
        if not isinstance(body, dict):
            self._reject(400, "body must be a json object")
            return

        robot_id = body.get("robot_id")
        request_id = body.get("request_id")
        arena_id = body.get("arena_id")
        if not isinstance(robot_id, str) or not robot_id:
            self._reject(400, "robot_id missing or invalid")
            return
        if not isinstance(request_id, str) or not request_id:
            self._reject(400, "request_id missing or invalid")
            return
        if not isinstance(arena_id, str) or not arena_id:
            self._reject(400, "arena_id missing or invalid")
            return

        canon = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

        with world.lock:
            if request_id in world.request_cache:
                cached = world.request_cache[request_id]
                if cached["path"] == path and cached["canon"] == canon:
                    world.log({"event": "replay", "path": path, "request_id": request_id})
                    self._send(cached["status"], cached["response"])
                    return
                self._reject(409, "request_id conflict")
                return

            unknown = self._check_unknown(path, body)
            if unknown:
                self._send(200, {"accepted": False, "real_timestamp_ms": int(time.time() * 1000), "virtual_time_s": 0})
                world.log({"event": "unaccepted", "path": path, "request_id": request_id, "reason": "unknown field %s" % unknown})
                return
            if arena_id != "default":
                self._send(200, {"accepted": False, "real_timestamp_ms": int(time.time() * 1000), "virtual_time_s": 0})
                world.log({"event": "unaccepted", "path": path, "request_id": request_id, "reason": "arena_id mismatch"})
                return
            if robot_id != world.robot_id:
                self._send(200, {"accepted": False, "real_timestamp_ms": int(time.time() * 1000), "virtual_time_s": 0})
                world.log({"event": "unaccepted", "path": path, "request_id": request_id, "reason": "robot_id mismatch"})
                return

            bad = self._check_structure(path, body)
            if bad:
                self._reject(400, bad, request_id)
                return

            status, response = self._business(path, body)
            world.request_count += 1
            if response.get("accepted") is True:
                world.request_cache[request_id] = {"path": path, "canon": canon, "status": status, "response": response}
            world.log({"event": "action", "path": path, "request_id": request_id, "request": body, "response": response})
            self._send(status, response)

    def _check_unknown(self, path, body):
        top_allowed = {"arena_id", "robot_id", "request_id"}
        if path in ("/measure", "/clear"):
            top_allowed |= {"position", "channel"}
        for k in body:
            if k not in top_allowed:
                return k
        if path in ("/measure", "/clear"):
            pos = body.get("position")
            if isinstance(pos, dict):
                for k in pos:
                    if k not in ("x", "y"):
                        return "position.%s" % k
        return None

    def _check_structure(self, path, body):
        if path in ("/measure", "/clear"):
            pos = body.get("position")
            if not isinstance(pos, dict):
                return "position missing"
            for axis in ("x", "y"):
                v = pos.get(axis)
                if not isinstance(v, (int, float)) or isinstance(v, bool):
                    return "position.%s invalid" % axis
                if not math.isfinite(v) or abs(v) > MAX_COORD:
                    return "position.%s out of range" % axis
            ch = body.get("channel")
            if isinstance(ch, bool) or not isinstance(ch, (int, float)):
                return "channel invalid"
            if isinstance(ch, float):
                if not ch.is_integer():
                    return "channel must be integer"
                ch = int(ch)
            if not (CHANNEL_MIN <= ch <= CHANNEL_MAX):
                return "channel out of range"
        return None

    def _business(self, path, body):
        world = self.world
        now_ms = int(time.time() * 1000)
        if path == "/enter":
            if world.entered:
                return 200, {"accepted": False, "real_timestamp_ms": now_ms, "virtual_time_s": 0}
            world.reset()
            world.entered = True
            world.real_enter_monotonic = time.monotonic()
            return 200, {
                "accepted": True,
                "real_timestamp_ms": now_ms,
                "virtual_time_s": 0,
                "max_virtual_duration_s": MAX_VIRTUAL_S,
                "max_real_duration_s": MAX_REAL_S,
                "remaining_real_duration_s": int(MAX_REAL_S),
            }
        if not world.entered:
            return 200, {"accepted": False, "real_timestamp_ms": now_ms, "virtual_time_s": 0}
        if world.exited:
            return 200, {"accepted": False, "real_timestamp_ms": now_ms, "virtual_time_s": 0}
        if path == "/exit":
            world.exited = True
            truth = world.scenario.truth()
            if not world.quiet:
                print("[MOCK] exit: cleared %d/%d  virtual=%.2fs  requests=%d" % (
                    truth["cleared"], truth["total"], world.virtual_time, world.request_count), flush=True)
            return 200, {"accepted": True, "real_timestamp_ms": now_ms, "virtual_time_s": round(world.virtual_time, 6), "exit_reason": EXIT_USER}
        x = float(body["position"]["x"])
        y = float(body["position"]["y"])
        channel = int(body["channel"])
        if path == "/measure":
            result = world.measure(x, y, channel)
        else:
            result = world.clear(x, y, channel)
        result["real_timestamp_ms"] = now_ms
        return 200, result


def make_server(port, world):
    Handler.world = world
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def build_world(args, robot_id="MOCKTEAM"):
    log_dir = args.log_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "mock_%d_%d.jsonl" % (args.port, int(time.time())))
    if args.scenario:
        with open(args.scenario, encoding="utf-8") as f:
            fixed = json.load(f)
        if isinstance(fixed, dict):
            fixed = fixed["sources"]
        scenario = Scenario(fixed=fixed)
    else:
        scenario = Scenario(seed=args.seed, count=args.count, mode=args.mode)
    world = World(scenario, log_path, quiet=args.quiet, rng_seed=(args.seed or 0) + 1)
    world.robot_id = robot_id
    world.log({"event": "scenario", "truth": scenario.truth(), "log_path": log_path})
    return world


def main():
    parser = argparse.ArgumentParser(description="local mock of the radio jammer simulator")
    parser.add_argument("--port", type=int, default=2026)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--count", type=int, default=None)
    parser.add_argument("--mode", choices=["q3", "q4"], default="q3")
    parser.add_argument("--scenario", default=None)
    parser.add_argument("--robot-id", default="MOCKTEAM")
    parser.add_argument("--log-dir", default=None)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    world = build_world(args, robot_id=args.robot_id)
    server = make_server(args.port, world)
    truth = world.scenario.truth()
    print("[MOCK] listening on http://127.0.0.1:%d  total=%d omni=%d dir=%d" % (
        args.port, truth["total"], truth["omni"], truth["dir"]), flush=True)
    print("[MOCK] Ctrl-C to stop", flush=True)
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()

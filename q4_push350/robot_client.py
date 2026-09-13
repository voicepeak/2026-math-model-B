#!/usr/bin/env python3
"""机器狗通信客户端（纯标准库，可在 macOS / Windows / Linux 直接运行）。

按《模拟器通信接口说明及编程指南》实现：
  - 四条指令 /enter /measure /clear /exit 的 HTTP+JSON 调用；
  - request_id 幂等与重试规则（网络失败复用原请求内容与原 request_id）；
  - 虚拟时间、当前位置、测向机当前频道的本地跟踪；
  - 剩余现实时间软截止；
  - 全部请求与响应写入 JSONL 日志。
"""
import json
import os
import time
import uuid
import urllib.error
import urllib.request


class RobotError(Exception):
    pass


class RobotClient:
    def __init__(self, base_url="http://127.0.0.1:2026", robot_id="<参赛队号>",
                 log_path=None, timeout=5.0, max_retries=3, retry_delay=0.5):
        self.base_url = base_url.rstrip("/")
        self.robot_id = robot_id
        self.log_path = log_path
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._seq = 0
        self._session_prefix = uuid.uuid4().hex[:12]
        self.virtual_time = 0.0
        self.position = (0.0, 0.0)
        self.channel = 1
        self.entered = False
        self.remaining_real_duration_s = None
        self._deadline_monotonic = None
        self.last_response = None
        if self.log_path:
            os.makedirs(os.path.dirname(os.path.abspath(self.log_path)), exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"event": "session_start", "base_url": self.base_url,
                                    "robot_id": self.robot_id}, ensure_ascii=False) + "\n")

    def _next_request_id(self, tag):
        self._seq += 1
        return "%s-%s-%d" % (self._session_prefix, tag, self._seq)

    def _base_payload(self, tag):
        return {"arena_id": "default", "robot_id": self.robot_id,
                "request_id": self._next_request_id(tag)}

    def _write_log(self, record):
        if not self.log_path:
            return
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def time_left(self):
        if self._deadline_monotonic is None:
            return None
        return max(0.0, self._deadline_monotonic - time.monotonic())

    def _post(self, path, payload):
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        attempt = 0
        while True:
            self._write_log({"event": "attempt", "path": path, "request": payload,
                             "attempt": attempt + 1})
            request = urllib.request.Request(self.base_url + path, data=body,
                                             headers={"Content-Type": "application/json"},
                                             method="POST")
            started = time.monotonic()
            status = None
            parsed = None
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as http_response:
                    status = http_response.status
                    raw = http_response.read()
                parsed = json.loads(raw.decode("utf-8"))
                break
            except urllib.error.HTTPError as exc:
                status = exc.code
                raw = exc.read()
                try:
                    parsed = json.loads(raw.decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    parsed = None
                if status == 429 and attempt < self.max_retries:
                    attempt += 1
                    time.sleep(self.retry_delay)
                    continue
                break
            except (ValueError, UnicodeDecodeError) as exc:
                self._write_log({"event": "invalid_response", "path": path,
                                 "request": payload, "error": repr(exc)})
                raise RobotError("Invalid JSON response on %s" % path) from exc
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
                attempt += 1
                if attempt > self.max_retries:
                    self._write_log({"event": "network_error", "path": path,
                                     "request_id": payload.get("request_id"), "request": payload,
                                     "error": repr(exc), "attempts": attempt})
                    raise RobotError("network failure on %s: %r" % (path, exc)) from exc
                time.sleep(self.retry_delay)
        wall_ms = (time.monotonic() - started) * 1000.0
        self.last_response = parsed
        self._write_log({"event": "http", "path": path, "request": payload,
                         "http_status": status, "response": parsed, "wall_ms": round(wall_ms, 2)})
        return status, parsed

    def _accepted(self, status, response):
        return status == 200 and isinstance(response, dict) and response.get("accepted") is True

    def enter(self):
        payload = self._base_payload("enter")
        status, response = self._post("/enter", payload)
        if self._accepted(status, response):
            self.entered = True
            self.virtual_time = float(response.get("virtual_time_s", 0.0))
            self.position = (0.0, 0.0)
            self.channel = 1
            self.remaining_real_duration_s = float(response.get("remaining_real_duration_s", 0.0))
            self._deadline_monotonic = time.monotonic() + self.remaining_real_duration_s
        return status, response

    def measure(self, x, y, channel):
        payload = self._base_payload("measure")
        payload["position"] = {"x": x, "y": y}
        payload["channel"] = channel
        status, response = self._post("/measure", payload)
        if self._accepted(status, response):
            self.virtual_time = float(response["virtual_time_s"])
            self.position = (float(x), float(y))
            self.channel = int(channel)
        return status, response

    def clear(self, x, y, channel):
        payload = self._base_payload("clear")
        payload["position"] = {"x": x, "y": y}
        payload["channel"] = channel
        status, response = self._post("/clear", payload)
        if self._accepted(status, response):
            self.virtual_time = float(response["virtual_time_s"])
            self.position = (float(x), float(y))
        return status, response

    def exit(self):
        payload = self._base_payload("exit")
        status, response = self._post("/exit", payload)
        if self._accepted(status, response):
            self.virtual_time = float(response.get("virtual_time_s", self.virtual_time))
        return status, response

    def close_log(self, note=""):
        self._write_log({"event": "session_end", "note": note, "virtual_time_s": self.virtual_time,
                         "position": list(self.position), "channel": self.channel})


def load_config(path=None):
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)

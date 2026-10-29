#!/usr/bin/env python3
"""Minimal GitHub REST client for the harness tools (standard library only).

Reads use GITHUB_TOKEN when set, otherwise anonymous access (public repositories).
With dry_run=True every write is recorded in .calls and nothing is sent; tests
also inject a fake `transport(method, url, body) -> (status, headers, data)`.
"""
import json
import os
import re
import time
import urllib.error
import urllib.request

API = "https://api.github.com"


def _urllib_transport(token):
    def send(method, url, body):
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
                   "User-Agent": "openamrobot-harness"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read()
                return response.status, dict(response.headers), (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            try:
                payload = json.loads(raw) if raw else None
            except ValueError:
                payload = {"message": raw[:200].decode(errors="replace")}
            return exc.code, dict(exc.headers or {}), payload
    return send


class GitHub:
    def __init__(self, token=None, dry_run=False, transport=None):
        self.token = token if token is not None else os.environ.get("GITHUB_TOKEN", "")
        self.dry_run = dry_run
        self.calls = []
        self.transport = transport or _urllib_transport(self.token)

    def _url(self, path):
        return path if path.startswith("http") else f"{API}{path}"

    def request(self, method, path, body=None):
        url = self._url(path)
        if method != "GET" and self.dry_run:
            self.calls.append((method, url, body))
            return {"dry_run": True, "number": 0, "html_url": "(dry run)"}
        for attempt in range(3):
            status, headers, data = self.transport(method, url, body)
            if status in (403, 429) and str(headers.get("X-RateLimit-Remaining", "1")) == "0" and attempt < 2:
                wait = max(0, int(headers.get("X-RateLimit-Reset", time.time())) - int(time.time())) + 1
                time.sleep(min(wait, 60))
                continue
            if status >= 400:
                raise RuntimeError(f"{method} {url}: HTTP {status}: {(data or {}).get('message', '')}")
            if method != "GET":
                self.calls.append((method, url, body))
            return data
        raise RuntimeError(f"{method} {url}: rate limited")

    def get(self, path):
        return self.request("GET", path)

    def paged(self, path, limit=1000):
        """Follow Link rel=next; returns a list (or the items list of search results)."""
        url, out = self._url(path), []
        while url and len(out) < limit:
            status, headers, data = self.transport("GET", url, None)
            if status >= 400:
                raise RuntimeError(f"GET {url}: HTTP {status}: {(data or {}).get('message', '')}")
            out += data.get("items", data.get("workflow_runs", data.get("artifacts", []))) if isinstance(data, dict) else data
            match = re.search(r'<([^>]+)>;\s*rel="next"', headers.get("Link", "") or headers.get("link", ""))
            url = match.group(1) if match else None
        return out[:limit]

    def download(self, url, accept="application/vnd.github+json"):
        """Bytes of a redirecting download (artifact zip). The token is sent to
        api.github.com only, never to the storage host it redirects to."""
        if getattr(self, "fake_download", None):
            return self.fake_download(url)
        request = urllib.request.Request(url, headers={"User-Agent": "openamrobot-harness", "Accept": accept})
        if self.token:
            request.add_unredirected_header("Authorization", f"Bearer {self.token}")
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read()

    def post(self, path, body):
        return self.request("POST", path, body)

    def patch(self, path, body):
        return self.request("PATCH", path, body)

    def delete(self, path):
        return self.request("DELETE", path)

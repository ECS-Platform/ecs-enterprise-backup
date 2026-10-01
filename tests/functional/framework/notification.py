"""Notification verification for the notification mechanism ECS actually implements.

ECS has NO email/SMS/webhook provider. Its notification surfaces are:
  * ``notice=`` text on the redirect URL of form posts (ApiResponse.notice) - the in-app toast/banner
  * the "Notifications" feed rendered from ``audit_trail.get_notifications()`` (partials/enterprise_widgets.html)
  * ``toast=`` flags (e.g. scheduler_ok / scheduler_retry_fail) on redirect URLs
  * a Microsoft Teams notification *action* that is logged in the audit trail ("Teams Notification Sent")
Anything else (email delivery, push) is reported as CapabilityBlocked rather than invented.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qs, urlparse

from .api_client import ApiResponse, EcsApiClient
from .assertions import assert_notification
from .errors import CapabilityBlocked


class NotificationHelper:
    def __init__(self, api: EcsApiClient, audit=None) -> None:
        self.api, self.audit = api, audit

    @staticmethod
    def from_response(resp: ApiResponse) -> dict[str, str]:
        q = parse_qs(urlparse(resp.location).query)
        return {"notice": (q.get("notice") or [""])[0], "toast": (q.get("toast") or [""])[0]}

    def feed(self, page: str = "/dashboard") -> list[dict[str, str]]:
        html = self.api.get(page).text
        block = re.search(r"Notifications</h6>(.*?)</div>\s*</div>\s*<div class=\"col-md-7\">", html, re.S)
        if not block:
            return []
        return [{"level": lvl.replace("notification-item", "").strip(),
                 "message": re.sub(r"<[^>]+>", "", msg).strip()}
                for lvl, msg in re.findall(r"<div class=\"(notification-item[^\"]*)\">(.*?)</div>", block.group(1), re.S)]

    def find(self, *, contains: str, page: str = "/dashboard") -> dict[str, str] | None:
        for n in self.feed(page):
            if contains.lower() in n["message"].lower():
                return n
        return None

    def assert_notified(self, resp: ApiResponse | None = None, *, contains: str, page: str = "/dashboard") -> Any:
        """Assert a notification containing ``contains`` was raised by the response notice or the notification feed."""
        pool: list[Any] = []
        if resp is not None:
            pool += [v for v in self.from_response(resp).values() if v]
        pool += self.feed(page)
        return assert_notification(pool, contains=contains)

    def email_delivery(self, *_a: Any, **_k: Any) -> None:
        raise CapabilityBlocked("ECS has no e-mail/SMS notification provider; only in-app notices and the notification feed exist.",
                                requires="e-mail notification service")

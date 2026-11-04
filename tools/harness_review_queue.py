#!/usr/bin/env python3
"""List the PRs the review mission should read next (deterministic).

A PR is queued when its repository has review: true, it is open, it has no
no-ai label, its head SHA has no harness review yet, and it is either from a
branch of the same repository or labelled ai-review by a maintainer (fork code is
otherwise never given to an agent). Drafts are queued only when labelled
ai-generated, because the review is the second opinion those PRs need.
ai-generated PRs come first, then the least recently updated.

  harness_review_queue.py [--limit N] [--fixtures DIR]
Prints a JSON list of {repository, pr, head, base, ros, ai_generated}.
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness_gh  # noqa: E402
import harness_lib as hl  # noqa: E402

MARKER = "<!-- harness-review head="


def names(item):
    return {l["name"] for l in item.get("labels", [])}


def queue(policy, gh, org, limit, bot=None):
    bot = bot if bot is not None else hl.bot_login()
    out = []
    for repo, cfg in policy["repositories"].items():
        if not cfg.get("review"):
            continue
        for pr in gh.paged(f"/repos/{org}/{repo}/pulls?state=open&per_page=100"):
            labels = names(pr)
            head = pr["head"]["sha"]
            same_repo = (pr["head"].get("repo") or {}).get("full_name", "").lower() == f"{org}/{repo}".lower()
            ai = "ai-generated" in labels
            if labels & {"no-ai", "hold"} or (pr.get("draft") and not ai):
                continue
            if not same_repo and "ai-review" not in labels:
                continue
            comments = gh.paged(f"/repos/{org}/{repo}/issues/{pr['number']}/comments?per_page=100")
            if any(f"{MARKER}{head}" in (c.get("body") or "") and hl.is_harness_comment(c, bot) for c in comments):
                continue
            out.append({"repository": repo, "pr": pr["number"], "head": head, "base": pr["base"]["sha"],
                        "ros": cfg.get("ros", ""), "ai_generated": ai, "updated_at": pr.get("updated_at", "")})
    out.sort(key=lambda item: (not item["ai_generated"], item["updated_at"]))
    return out[:limit]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--org", default="openAMRobot")
    parser.add_argument("--root", default=str(hl.ROOT))
    args = parser.parse_args(argv)
    print(json.dumps(queue(hl.load_policy(Path(args.root)), harness_gh.GitHub(), args.org, args.limit), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

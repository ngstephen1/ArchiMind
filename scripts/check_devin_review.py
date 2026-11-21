"""Show the current Devin result and review threads that block a main PR."""

import argparse
import json
import subprocess

DEVIN = "devin-ai-integration"
STATUS = "Devin Review"
THREADS = """
query($owner: String!, $name: String!, $number: Int!, $endCursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      headRefOid
      reviewThreads(first: 100, after: $endCursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          isResolved
          comments(first: 1) { nodes { author { __typename login } url path } }
        }
      }
    }
  }
}
"""


def preflight(repository, number):
    owner, name = repository.split("/", 1)
    summary = json.loads(
        subprocess.check_output(
            [
                "gh",
                "pr",
                "view",
                str(number),
                "--repo",
                repository,
                "--json",
                "headRefOid,baseRefName,state,isDraft,statusCheckRollup",
            ],
            text=True,
        )
    )
    if (
        summary["baseRefName"] != "main"
        or summary["state"] != "OPEN"
        or summary["isDraft"]
    ):
        print("Select an open, ready-for-review PR targeting main.")
        return 1

    pages = json.loads(
        subprocess.check_output(
            [
                "gh",
                "api",
                "graphql",
                "--paginate",
                "--slurp",
                "-f",
                f"query={THREADS}",
                "-f",
                f"owner={owner}",
                "-f",
                f"name={name}",
                "-F",
                f"number={number}",
            ],
            text=True,
        )
    )
    head = summary["headRefOid"]
    threads = []
    for page in pages:
        pr = page["data"]["repository"]["pullRequest"]
        if pr["headRefOid"] != head:
            print("The PR head changed during inspection. Run the preflight again.")
            return 1
        threads.extend(pr["reviewThreads"]["nodes"])

    statuses = [
        status
        for status in summary["statusCheckRollup"]
        if status.get("context") == STATUS
    ]
    state = statuses[0]["state"] if len(statuses) == 1 else "MISSING OR AMBIGUOUS"
    print(f"PR #{number} · {head} · {STATUS} {state}")
    for thread in threads:
        if thread["isResolved"]:
            continue
        for first in thread["comments"]["nodes"]:
            author = first["author"] or {}
            reviewer = (
                "Devin"
                if author.get("__typename") == "Bot" and author.get("login") == DEVIN
                else "Other reviewer"
            )
            print(f"{reviewer} · {first['path']} · {first['url']}")
    if state != "SUCCESS" or any(not thread["isResolved"] for thread in threads):
        return 1

    print("No unresolved review threads. Read Devin’s summary before merging.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("number", type=int)
    parser.add_argument("--repo", default="ngstephen1/ArchiMind")
    args = parser.parse_args()
    raise SystemExit(preflight(args.repo, args.number))

# Review Devin’s findings before merging

GitHub requires the **Devin Review** status from the Devin.ai Integration app and resolution of every inline review conversation before a pull request can merge into `main`. The status belongs to the current commit, so a push can require a new Devin run. The conversation rule also covers other reviewers. Direct pushes to `main` are blocked by the pull-request requirement.

1. Wait for Devin to finish on the current commit. Read its latest report and inspect open conversations, including findings on earlier commits.
2. Check each finding against the code. Fix confirmed defects and run the relevant tests. For a false positive or a follow-up, reply with the reasoning or issue link. Resolve the thread after recording its disposition. Discuss recommendations that appear only in the summary in the PR conversation.
3. Check the final commit. The preflight prints the current status and links to unresolved review threads. GitHub is the merge authority and verifies the app identity.

```sh
python scripts/check_devin_review.py 123
```

## Repository settings

The `Devin review before main merge` ruleset is recorded in [.github/rulesets/main-devin-review.json](../../.github/rulesets/main-devin-review.json). Repository admins can create it with the following command when setting up a fresh repository. Update an existing ruleset by ID instead of creating a duplicate.

```sh
gh api --method POST repos/ngstephen1/ArchiMind/rulesets \
  --input .github/rulesets/main-devin-review.json
```

If Devin is missing or reports an error, request a new review from the installed app and confirm its status on the latest head. Any emergency ruleset change requires a repository administrator and should be documented in the PR. The preflight uses the existing GitHub CLI login. It does not call Devin’s API or need a separate Devin key.

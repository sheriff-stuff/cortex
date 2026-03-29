Find and review all open PRs created during this conversation. If no PRs were created in this session, fall back to the open PR associated with the current branch. For each PR, review all comments left by reviewers — both inline review comments and top-level PR comments.

## Before starting

1. Check if the PR branch has merge conflicts with the base branch. If there are conflicts, resolve them first before addressing any comments.
2. Check if any bots (e.g. Copilot coding agent) have opened PRs that duplicate work already done in this session. If so, comment explaining the work is already covered (link to the relevant PR) and close the duplicate.

## For each comment:

1. **Assess** whether the feedback is valid and worth fixing, or whether it's a nitpick/incorrect/not applicable. Also consider whether it's **in scope** for this PR.

2. **If worth fixing (in scope)**: Make the code change on the current branch, then reply to the comment on GitHub tagging the reviewer (e.g. "@reviewer Fixed — removed the unused parameter, good catch.").

3. **If valid but out of scope**: The feedback is correct, but fixing it here would go beyond the purpose of this PR (e.g. a pre-existing issue, a separate concern, or a feature request). In this case:
   - Create a new branch for the fix. Prefer branching from the base branch (e.g. `master` or `main`). Only branch from the current PR branch if the fix depends on the changes in this PR.
   - Open a separate PR for it.
   - Reply to the comment on GitHub tagging the reviewer, explaining that it's out of scope for this PR but has been addressed separately, and link to the new PR (e.g. "@reviewer Good catch — this is a pre-existing issue outside the scope of this PR. Opened #42 to address it.").

4. **If NOT worth fixing**: Reply to the comment on GitHub tagging the reviewer with a polite, constructive explanation of why you disagree or why the change isn't necessary. Be respectful but direct — don't just agree for the sake of it. Back up your reasoning with specifics (e.g. "@reviewer I think this is fine as-is because...").

## Comment formatting

Every comment and reply you post on the PR MUST start with:

> 🤖 *beep boop — this is Claude, not a human*

This makes it clear the response was AI-generated, not from the repo owner.

## After handling all comments

Push the changes (if any). Then leave a single top-level comment on the PR summarizing what was done — list which comments were addressed with fixes, which were split into separate PRs (with links), and which were pushed back on, with brief reasoning. This gives the reviewer a quick overview without needing to re-read every thread.

Do NOT give me a summary yet — proceed to the polling loop below.

## Polling loop

After completing a review pass, automatically re-check for new or unresolved comments. This loop runs up to **5 cycles** total (including the initial pass).

### On each cycle:

1. **Check for unresolved comments**: Use `gh` to fetch all review comments and top-level PR comments. A comment is "unresolved" if it has no reply from you (the bot) yet, or if a reviewer has replied *after* your last reply on that thread.

2. **If no unresolved comments remain**: The review is complete. Output the final summary (what was fixed, what was spun off, what was pushed back on) and stop.

3. **If there ARE unresolved comments** (or this is the end of the first pass):
   - Push any pending changes first.
   - Display the cycle count and sleeping indicator, then wait 2 minutes:

```
    ╭──────────────────────────╮
    │  (-_-) zzZ               │
    │  Claude is sleeping...   │
    │  Next review check in    │
    │  2 minutes               │
    │  [Cycle 1/5]             │
    ╰──────────────────────────╯
```

   - Run `sleep 120` to wait.
   - After waking, output:

```
    ╭──────────────────────────╮
    │  (o_o) !                 │
    │  Claude is awake!        │
    │  Checking for new        │
    │  comments...             │
    ╰──────────────────────────╯
```

   - Then go back to the top of this command ("Before starting") and run the full review process again.

4. **After 5 cycles**: Stop regardless and give the final summary. If there are still unresolved comments, list them and let me know.

### Cycle counter

Track which cycle you're on (1 through 5). Display it in the sleeping indicator so I can see progress. The first full review pass counts as cycle 1.

## Final summary (output only when the loop ends)

Give me a summary of what you fixed, what you spun off into separate PRs, and what you pushed back on. If the loop ended because all comments were resolved, say so. If it ended because the 5-cycle cap was hit, list any remaining unresolved comments.

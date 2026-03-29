When /review-pr is invoked, review all PRs created during this session (not just the most recent one). Check each for new reviewer comments and handle them.

When reviewing PR comments, if valid feedback is out of scope for the current PR (e.g. pre-existing issues just moved during a refactor), create a follow-up PR with the fix on a separate branch instead of pushing back. Link the follow-up PR in a reply on the original review comment.

All comments and replies posted by Claude on GitHub (PR comments, review replies, PR descriptions) must start with "🤖 beep boop — this is Claude, not a human." followed by the actual message. This makes it clear the response is AI-generated. When replying to a reviewer's comment, address them by username (e.g. "@copilot", "@gemini-code-assist").

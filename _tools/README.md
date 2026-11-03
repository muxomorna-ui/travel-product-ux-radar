# Release checks

Run `python3 _tools/prepare_release.py SOURCE STAGING --date YYYY-MM-DD`.
STAGING must be a temporary directory. This does not install or publish a release.

The producer must have finished (`execution.json`). A failed launcher is distinct
from a broken page: only a single browser-launch failure can proceed to staging;
data failures, JavaScript syntax errors and unexpected producer errors stop it.
Original producer validation files are never rewritten as successful.

Every new staged release requires a real browser check before publication. Serve
STAGING on localhost and use the connected browser through `cua_repl`, not a
hard-coded system Chrome executable. Verify all navigation tabs after their
heading becomes visible, a month filter, JSON download versus the visible count,
and absence of the tours filter in Air/Rail (and presence in Tours). Check browser
console errors. A failed/unavailable independent browser check blocks publication.

After success, record the tested HTML SHA-256 and checks in a local receipt next
to `release-check.json`. Only copy files listed in that manifest, after checking
their SHA-256 again. Commit only these public files; exclude receipts and logs.
Push is not completion: poll Pages and compare every published file's SHA-256.
Skip unchanged versions; preserve unrelated working-tree changes.

Tests: `python3 -m unittest discover -s _tools -p 'test_*.py'`.

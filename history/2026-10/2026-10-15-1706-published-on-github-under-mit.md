# Published on GitHub as github.com/stepankandrushin/drover, under the MIT license

2026-10-15. The owner asked to publish drover as open source on their GitHub and to add a license
if there was none yet. This closes the "A license, before it is published" item in the entry of
14:29.

## Checked before the first push

A commit on GitHub cannot be taken back: after a force-push it is still served by its SHA. So the
three commits so far were read in full first, the diffs and the commit messages. The search was
for addresses, host and server names, home and cloud paths, and the names of the owner's repos
from the workspace inventory. It found none of the hosts, addresses or paths. The only repo names
it found were ordinary words used as examples (infra, web, docs, telegram, frigate). The history
went up as it was, with no fresh first commit.

## What changed

- LICENSE: MIT, the same text as the owner's other one-file Python tool on GitHub.
- README.md: the install step clones from GitHub, and a License section at the end.
- AGENTS.md: "Meant to be published" became "Public, MIT", with where origin pushes and why a
  pushed commit stays.
- The GitHub repo was created empty with `gh repo create --public`, along with a description and
  topics. It is origin's third url, after the two private git servers, so one `git push` updates all three.
  The first try used `set-url --add --push`. That added a pushurl, which replaced both servers as
  push targets. It was undone before anything was pushed.

Routing is unchanged, so no `drover eval` was run. 19 tests pass.

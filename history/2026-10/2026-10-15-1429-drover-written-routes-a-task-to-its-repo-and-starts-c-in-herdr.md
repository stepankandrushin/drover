# drover written: routes a task to its repo and starts the agent there in a new herdr tab

2026-10-15. Asked for: a command that takes a task, finds the repo it belongs to (or a new space in
herdr for it) and starts the agent there with the owner's `c` alias. It should use scripts first and
the local abliterated Qwen only when scripts are not enough, and be fit to publish later. How it is
set up on the owner's machines is in the dotfiles repo's history entry of the same day.

## What was built

- `drover`, one Python 3.9+ stdlib file. Places are the subdirectories of `roots` that have a
  `.git`, AGENTS.md, CLAUDE.md or README, plus the `places` listed. Each one's description is the
  first paragraph of its agent file or README, skipping the "This file provides guidance to Claude
  Code" boilerplate.
- Routing: `@place`, `-C` or a work-here path ("work in X", "repo: X", "cd X", "In X: …") decides
  alone. Otherwise path, name, keyword and history signals decide only when they all agree. When
  they disagree, or there are none, the model decides with the signals as hints.
- History: the first prompt of every interactive Claude Code session (entrypoint `cli`, not the
  headless `sdk-cli` ones) with its cwd, BM25 over them. The index is cached in
  ~/.cache/drover/history.json by file mtime.
- Model: the place catalog in the system message, so llama.cpp's prompt cache keeps it between
  calls. The user message holds the herdr agents' titles, sessions per place over 30 days, the six
  most similar past tasks with their places, and the rules' hints. The answer is constrained by a
  `json_schema` whose `place` is an enum of the place names. Endpoints are tried in order, because
  one GPU server may have its model unloaded for a while.
- Launch: the task goes to ~/.local/state/drover/tasks/; the tab is created in the workspace
  labelled with the place, or one with a pane in its directory, or a new workspace. drover waits
  for the shell's prompt and types `{command} "$(cat <file>)"`, so an alias works, then polls
  `herdr agent get` until the agent shows. Every decision goes to ~/.local/state/drover/log.jsonl.
- `drover eval` replays the history through the router. The index at each session holds only
  earlier sessions.

## Why it decides the way it does: the figures

On the owner's history, 168 places. The labels are where each session happened to run, often a
catch-all repo before a dedicated one existed, so a "miss" is often drover being right.

- First cut, any whole-word name deciding alone: 21% right, because some repo names are ordinary
  words in tasks (a messenger's or a video site's name used as the channel, not the repo). The
  fix: a name decides only if past tasks naming it mostly ran there, or, with under three such
  tasks, if it has a dot, dash, underscore or digit.
- Path versus a confident history match, all sessions: when they disagreed, history matched the
  label 23 of 26 times. The cases split two ways. Marketplace chats that cite a file from the
  documents tree really belong in the browser-automation repo. But a task that says "Repo X (read
  AGENTS.md first)" belongs in X, even if it was run from the catch-all. So a work-here path
  decides alone, and other signals decide only together.
- Model with only the hints: 44% on the 216 tasks it got (sessions since 2026-10-05). With the six
  most similar past tasks as examples: 60%, against 55% for taking the history's top place.
- history_min_share 0.75 → 0.6 (score 12 kept): 37 more tasks decided by history at 84%, which
  the model got right about 60% of the time.
- Final, the 456 sessions since 2026-10-05 with three or more content words: path 151 (76%
  agree), name 15 (47%), history 105 (86%), model 185 (57%); overall 317 of 456, 69.5%. The rules
  settle 60% of the tasks in 0.17 s. A model call, with a 27B Qwen on an A100, takes about 1.5 s
  once the catalog is cached (8 s for the first).

## Tested

- 16 unit tests on a made-up tree (tests/test_route.py).
- herdr 0.9.3, with `command = echo TEST`: a new workspace with the task's quotes and `$HOME`
  arriving intact, then a second task as a second tab in that workspace. With the real agent,
  Claude Code was detected 0.7 s after the launch and answered. The test workspace was closed
  afterwards.
- macOS system Python 3.9.6: dry runs route.

## Open

- A license, before it is published.
- Sessions drover starts become history, so a misroute that is left running teaches the next
  routing the same mistake.

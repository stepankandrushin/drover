# drover

Routes a task to the project it belongs to and starts a coding agent there, in the calling
terminal or with `-t` in a new herdr tab:
rules first (explicit, paths, names, keywords, Claude Code history), a local LLM only when they do
not agree. One file, `drover`, Python 3.9+ standard library only. README.md is the user's manual;
this file is how to work on it.

- **Public**, MIT: origin pushes to github.com/stepankandrushin/drover as well as the two git
  servers, and a pushed commit cannot be taken back (GitHub serves it by SHA after a force-push).
  Keep tracked files and commit messages, history/ included, free of the owner's hosts, addresses, names,
  repos and tasks. The owner's own config is drover/config.ini in the dotfiles repo beside this
  one (linked as ~/.config/drover/config.ini by its install.sh), and the owner runs drover as the
  alias `d`; that setup's history is there too.
  Examples in README.md and config.example.ini use neutral names.
- **Python 3.9, standard library only.** macOS's system Python (Xcode's) is 3.9: no `match`, no `X | Y`
  annotations, no `tomllib` (that is why the config is INI). No third-party imports.
- **Rules decide only when they agree** (README.md, "How it decides"). A new rule becomes another
  signal in `route()`, not a stage that decides alone, unless it is an explicit statement by the
  user of where to work (`@place`, "work in X").
- **Measure before and after any change to routing** with `drover eval` (rules only, about a second)
  and `drover eval --model --since <date>` (about 5 minutes for 450 sessions on the local Qwen).
  The labels are where the owner happened to run a session, so a "miss" is often drover being
  right: read `--wrong` before tuning to the numbers. The figures each change produced go in
  its history/ entry.
- **The calling shell changes directory through the shell function in README.md**: drover writes
  `cd <place> && <launch line>` to the file named in `$DROVER_RUN_FILE` and the function evals it.
  Without that variable, drover execs `$SHELL -ic <line>` in the place. Without a terminal on
  stdin it opens a tab as with `-t`, so that a script or an agent calling drover does not hang.
- **herdr is driven through its CLI**, which prints JSON (`{"result": …}`); `herdr --skill` and
  `herdr <group>` print the current syntax. drover waits for the new pane's shell to draw its prompt
  (`pane wait-output --regex \S`) before typing, and reads the agent's kind from
  `agent get <pane>` → `.result.agent.agent`.
- Tests: `python3 -m unittest discover -s tests`. They build a tree of made-up places in a temp
  directory and never touch herdr or a model.
- A test that launches into herdr for real: point `DROVER_CONFIG` at a copy of the config with
  `command = echo TEST`, run with `-t -C <place>`, read the pane, and close the workspace or tabs
  you made (`herdr workspace close <id>`).

## Docs

- README.md: the user's manual, covering use, configuration, how routing decides, and privacy.
- config.example.ini: every key with its default.
- history/: how it got this way, with the eval figures of each change.

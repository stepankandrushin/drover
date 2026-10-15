# The agent starts in the calling terminal, after a cd to the place; -t opens a herdr tab as before

2026-10-15. Asked for: by default, drover should not open a new herdr workspace or tab. Instead it
should exit and leave the terminal it was typed in, in the place's directory, running the agent.
The tab behavior stays behind an option. `-n` was the suggestion, but it is the dry run, so the
option is `-t, --tab`.

## What changed

- A program cannot change its parent shell's directory, so the shell does the `cd` itself. drover
  writes `cd '<place>' && <launch line>` to the file named in `$DROVER_RUN_FILE`, and a shell
  function in README.md (the same idea as zoxide's or broot's) evals it once drover exits. The
  function uses `mktemp`, not a fixed name in /tmp, and passes drover's exit code through when
  nothing was written (`-n`, `places`, `eval`, errors).
- Without the variable, drover `chdir`s to the place and execs `$SHELL -ic <line>`. `-i` keeps
  aliases working. The agent runs here, and when it exits the terminal is back where it was.
- With no terminal on stdin, as from a pipe, a script or another agent's shell tool, drover
  opens a tab as with `-t`. An interactive agent started there would hang or get EOF.
- `-f` now implies `-t`.
- `write_task()` is split out of `launch()`. `launch()` takes the ready line, and the task file
  goes into the log entry in both modes. A here-run is logged with `"where": "here"`.
- herdr is needed only for `-t` now. `herdr_context()` already did nothing without it.
- README.md (the opening example, Install with the function, Use, the configuration table),
  config.example.ini (the `command` and `launch` comments), AGENTS.md (the bullet on how the cd
  reaches the shell, `-t` in the real-launch test). New test: `run_here()` with
  `$DROVER_RUN_FILE`, with the written line run by `sh` from `/`, into a directory whose name has a
  quote and a space. 20 tests, passing.

## Checked

In a pty, with an interactive zsh reading a function like the README's and a config with
`command = echo TEST`, using `-C` so no model was asked:

- `d -C <place> hello there`, then Ctrl-D: printed `TEST hello there`, and afterwards
  `$PWD` was the place.
- The script run directly, without the function: `TEST hello there`, and `$PWD` stayed `/`.
- `d -n -C <place> hi`: printed the path, ran nothing, returned 0, `$PWD` unchanged.
- `echo | d -C <place> tab test`: opened a tab in the place's existing workspace. Its pane showed
  `TEST tab test`. The tab was closed afterwards.
- Re-reading the zshrc in a shell that still had an alias of the same name left the function in
  place (`unalias`, and `function name {` so the alias is not expanded while it is defined).

Routing is unchanged, so no `drover eval` was run.

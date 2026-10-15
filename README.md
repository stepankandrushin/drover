# drover

One command to hand a task to a coding agent in the project it belongs to.

```sh
drover the gate camera stopped recording since yesterday
  more lines, or two empty lines or Ctrl-D to route it
→ frigate  [model: 127.0.0.1:8080]  1.3s
  similar past tasks ran in: infra (40%), frigate (22%), media (21%), voice (9%)
~/code/frigate $ claude "$(cat ~/.local/state/drover/tasks/…-gate-camera-stopped-recording.md)"
```

When you work across dozens of repositories, every task starts with the same small decision:
which directory do I open the agent in? drover makes that decision and hands off. It finds the
project, changes to its directory in the terminal you typed in, and starts your agent there with
the task as its first prompt. With `-t` it starts the agent in a new tab of that project's
[herdr](https://herdr.dev) workspace instead, creating the workspace if there isn't one, and your
terminal stays free for the next task. The agent never sees the routing. It starts in the right
place with a clean context and spends no tokens working out where it should be.

drover is a single Python file with no dependencies. Plain rules do most of the routing, and a
language model is asked only when the rules can't decide. Any OpenAI-compatible endpoint works,
and a small local model is enough.

## How it decides

The candidates are **places**: every directory under your configured roots that has a `.git`,
an `AGENTS.md`, a `CLAUDE.md` or a README, plus any directories you list. A place's description
is the first paragraph of its `AGENTS.md`, `CLAUDE.md` or README, and you can override it in the
config.

1. **Explicit.** `@place` at the start of the task, or `-C place-or-dir`, decides outright.
2. **A work-here path.** A path written as "work in X", "repo: X", "cd X" or "In X: …" decides
   outright.
3. **Signals.** Each of these names one place or none:
   - **path**: the place the task's paths lie in, counting absolute and `~` paths and relative
     paths that exist in exactly one place (`next-prompts/2026-10-15-x.md`, `servers/office.md`).
   - **name**: a place named in the task. A plain word such as `telegram` or `web` is often
     just a word, so a name counts only if past tasks that used it mostly ran in that place, or,
     with no such history, if it looks like a repo name (`acme.dev`, `billing-api`, `robot2`), or
     if it is written `@name` or "the name repo".
   - **keyword**: a pattern from `[keywords]` in the config.
   - **history**: the first prompts of your past Claude Code sessions are indexed with BM25,
     with the directory each one ran in. If the ten most similar ones mostly ran in one place,
     and the match is strong enough, that place is the signal.

   **If every signal present names the same place, that place wins.** If they disagree, or there
   are none, the rules aren't enough and the model decides.
4. **The model** gets every place's one-line description, the signals the rules found, the six
   most similar past tasks with where each ran, how many sessions each place had in the last
   30 days, and what the agents open in herdr are working on. It answers with JSON, constrained
   by a schema to an existing place name, plus a short title for the tab.
5. **Fallbacks.** Without a model answer, drover takes the first signal, then the history's best
   match, then the configured default place.

On the author's 450 most recent sessions across 168 places, the rules settled 60% of the tasks
alone in under 0.2 seconds, and the model, a 27B Qwen on a local GPU, took the rest. A model call
takes about 1.5 seconds once the place catalog is in the server's prompt cache, and a few seconds
before that.

## Install

Requirements: Python 3.9 or later. `-t` also needs herdr 0.9 or later with its server running.

```sh
git clone https://github.com/stepankandrushin/drover ~/src/drover
ln -s ~/src/drover/drover ~/.local/bin/drover
mkdir -p ~/.config/drover && cp ~/src/drover/config.example.ini ~/.config/drover/config.ini
$EDITOR ~/.config/drover/config.ini      # roots, the agent command, the model endpoint
drover places                            # what drover found, and what the model will be told
```

A program cannot change the directory of the shell that started it, so drover leaves the line
`cd <place> && <agent>` in a file and a shell function runs it once drover exits. Put this in
`~/.zshrc` or `~/.bashrc`:

```sh
drover() {
  local f rc line
  f=$(mktemp) || return
  DROVER_RUN_FILE=$f command drover "$@"
  rc=$?
  line=$(cat "$f"); rm -f "$f"
  if [ -n "$line" ]; then eval "$line"; else return $rc; fi
}
```

Without the function, drover starts the agent in the place's directory in a shell of its own, and
when the agent exits you are back where you were.

## Use

```sh
drover task text             # route, cd there, start the agent here: more lines, then Enter x3
drover                       # type or paste the task below, then Enter x3
drover -t "task text"        # start the agent in a new herdr tab instead
drover -f "task text"        # -t, and switch to the new tab
drover -n "task text"        # dry run: print the place and why, start nothing
drover @infra "task text"    # skip routing
drover -C ~/some/dir "..."   # any directory, even one outside the places
drover --no-model "..."      # rules and history only
drover places                # list the places and their descriptions
drover eval                  # replay your history through the rules
drover eval --model --since 2026-10-01 --wrong
```

On a terminal the words after `drover` are the task's first line, with or without quotes, and
drover then reads more lines until two empty lines in a row, that is Enter three times at the end
of the text: a one-line task is `drover task text` and three Enters. Ctrl-D ends it too, at the end
of the text or on a line of its own. Empty lines in a paste don't end it, because the paste's next
line is already waiting behind them; drover ends the task at two empty lines only when nothing
follows them for 0.2 s. Keys pressed while drover works are thrown away, so one Enter or Ctrl-D too
many doesn't reach the shell. Every word from the first one that is not an option belongs to the
task, `-n` and `--` too. The shell still reads that first line, though, so one with
`' ( ) ; & | < > # * ? $ !` in it goes in quotes or below a bare `drover`, and so does a paste of
many lines: pasted after `drover ` on the command line, its other lines would run as shell
commands. From a pipe or a script, the words alone are the task, and with none it is read from
stdin. There is no terminal there for the agent, so it starts in a herdr tab, as with `-t`.

From the end of the task on, one line on the terminal says what drover is doing (routing, asking the model at
an endpoint, and with `-t` opening the tab and waiting for the agent), and the result replaces it.

The task is written to `~/.local/state/drover/tasks/<time>-<title>.md`, and the agent starts with
`{command} "$(cat <that file>)"`, run by your shell after the `cd`, or with `-t` typed into the new
pane's shell. Because the line goes through your interactive shell, an alias works as the command
(for example `c` for `claude --dangerously-skip-permissions`). Every decision is appended to
`~/.local/state/drover/log.jsonl`.

With `-t`, the new tab goes into the first workspace whose label is the place's name, or that has
a pane in the place's directory. With no such workspace, drover creates one named after the place.
Existing tabs and agents are left alone, so every task starts fresh.

## Configuration

`~/.config/drover/config.ini`, or the file named in `$DROVER_CONFIG`. See
[config.example.ini](config.example.ini) for every key with its default.

| Section | Key | Meaning |
|---|---|---|
| drover | roots | directories whose subdirectories are places |
| drover | places | extra single directories that are places |
| drover | ignore | glob patterns of directory names to skip |
| drover | default | the place used when nothing decides |
| drover | command | the agent command: `claude`, an alias, `codex` |
| drover | launch | the line your shell runs, `{command} "$(cat {file})"` by default |
| drover | history | where Claude Code keeps its transcripts |
| drover | history_min_score, history_min_share | how strong and how one-sided the similar past tasks must be to count as a signal |
| model | endpoints | OpenAI-compatible base URLs, tried in order |
| model | model, api_key, timeout | as the endpoint wants them |
| model | extra | JSON merged into the request body, e.g. `{"chat_template_kwargs": {"enable_thinking": false}}` for Qwen3 on llama.cpp or vLLM |
| keywords | `<place> = word, word, /regex/` | words and patterns that point to a place |
| describe | `<place> = text` | a description to use instead of the one from the place's docs |
| moved | `<old path> = <new path>` | directories that moved, so old history still counts |

## Measuring it on your own history

`drover eval` takes the first prompt of each interactive Claude Code session on this machine,
routes it as drover would have at the time (the history index holds only the sessions before
it), and compares the answer with the directory the session actually ran in. Add `--model` to
include the model stage. It's slow, about a second per task the rules leave open.

Read the numbers as agreement with your habits, not as accuracy. A task you ran from a catch-all
repo because the right one didn't exist yet counts as a miss when drover picks the right one.
`--wrong` lists the disagreements so you can judge them.

## Privacy

Everything runs locally except the model call. That call sends the place names and
descriptions, the task, and up to six of your past first prompts, each cut to 220 characters, to
the endpoints you configure. Use a model you run yourself if your tasks are private. The history
cache is `~/.cache/drover/history.json`.

## Tests

```sh
python3 -m unittest discover -s tests
```

## License

MIT, see [LICENSE](LICENSE).

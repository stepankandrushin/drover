# A status line from Ctrl-D on, and tasks typed after `drover` without quotes and over many lines

2026-10-15. Two requests after a real run. A pasted task ended with Ctrl-D, and then nothing
showed for almost 10 seconds until the result came. The owner pressed Ctrl-D again and again,
not knowing whether drover had taken it. They also wanted to write `drover this is a task`,
without quotes, and go on onto more lines.

## What changed

- `status()`: when stderr is a terminal, a single line says what drover is doing, and each new
  step overwrites it: `routing …` at the moment the task is read, `asking the model at <host> …`
  once per endpoint tried, `opening a tab in herdr …`, `waiting for the agent to start in <tab> …`.
  The result lines replace it, and so does a warning or an error. On exit, a `finally` in
  `__main__` clears whatever status is still showing, so an error message starts on a clean line.
  Measured in a pty: the status appeared in the same 10 ms as the Ctrl-D.
- `read_task()`: on a terminal, the words after the options are the task's first line, and drover
  reads more lines until Ctrl-D, so a one-line task now takes Enter and then Ctrl-D. A hint line
  says so. A bare `drover` prompts as before. If Ctrl-D ends a line that has no Enter (pressed
  twice), drover writes a newline first, so the status doesn't overwrite the last line of the
  task. From a pipe or a script, nothing changed: the words alone are the task, and with no words
  the task comes from stdin.
- The task argument is `argparse.REMAINDER`: every word from the first non-option on belongs to
  the task, `-n`, `-C` and `--` included, because unquoted text can hold them. Only a `--` in front
  of the task is dropped.
- README.md (the opening example, Use, and the notes under it), the usage text at the top of the
  file, and two unit tests (18 in all, passing).

## Checked

- In a pty, a dry run with the real model: hint, `routing …` at Ctrl-D, `asking the model …`, then
  the result. Ctrl-D twice after text with no Enter: a newline, then the status on its own line.
- A real launch into herdr with `command = echo TEST`, using `-C` to a place and
  `fix the "it's" thing -n --` plus a second line `(second line) with $HOME and a #`. The pane
  echoed both lines exactly as typed. The test tab was closed afterwards.
- Extra Ctrl-D presses made while drover is still working do not close the shell afterwards
  (tested in a pty under bash 5.2), so nothing discards typed-ahead input.
- The shell still parses the first line: `' ( ) ; & | < > # * ? $ !` there needs quotes, or the
  task goes below a bare `drover`. A paste of many lines right after `drover ` on the command line
  can't work: with bracketed paste, bash 5.2 runs each later line as its own command (tested). The
  README says both.

Routing itself is unchanged, so no `drover eval` was run.

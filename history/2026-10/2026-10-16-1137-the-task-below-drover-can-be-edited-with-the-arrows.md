# The task typed below `drover` can be edited: arrows, Home and End, the usual shell keys

2026-10-16. The owner reported that, while typing a task after a bare `drover`, the arrows printed
`^[[D` and the like instead of moving the cursor.

## Why

`read_tty()` read the terminal in its own line (canonical) mode, which edits a line with
Backspace, Ctrl-U and Ctrl-W only and hands every other key over as it comes, an arrow being
`ESC [ D`, echoed as such. Python's `readline` module was considered and not used. It edits one
line at a time, Up and Down recall history instead of moving between the task's lines, and Ctrl-D
at the end of a typed line deletes a character rather than ending the task, which would undo the
entry of 2026-10-15 16:32. Its key bindings also differ between GNU readline (Linux) and libedit
(macOS's system Python).

## What changed

- `read_tty()` switches the terminal out of line mode and echo (`ICANON`, `ECHO`, `ISIG`,
  `IEXTEN`, and `ICRNL`/`INLCR` so that Enter comes as `\r`) for the time the task is read, turns
  on bracketed paste, and restores both in a `finally`. `TCSANOW` keeps what was typed before
  drover got there, and a Ctrl-D typed that early arrives as NUL, which also ends the task.
- `Editor`, a line editor for the task's lines: text and Tab insert; Left and Right cross into the
  lines next to the cursor; Up and Down go by screen row, through wrapped lines and into the lines above
  and below; Home/End and Ctrl-A/Ctrl-E; Backspace and Delete join lines at their edges; Ctrl-U,
  Ctrl-K, Ctrl-W and Alt-Backspace; Ctrl or Alt with the arrows and Alt-B/Alt-F by words; Ctrl-B,
  Ctrl-F, Ctrl-P, Ctrl-N. Escape sequences it does not know are dropped, not printed. Ctrl-C
  raises KeyboardInterrupt as before (`ISIG` is off, so the editor does it itself and Ctrl-Z
  cannot stop drover with the terminal left raw).
- Enter starts a new line at the end of the text wherever the cursor is, so the existing ending
  rule holds: two empty lines at the end, that is Enter three times, after a typo fixed further back
  too. Ctrl-D ends the task wherever the cursor is.
- A marked paste (`ESC[200~ … ESC[201~`) goes in at the cursor as text, line breaks and empty lines
  included, and never ends the task. For a terminal that does not mark pastes, the 0.2 s check
  stays: two empty lines with more input waiting behind them are part of a paste.
- Drawing: input already waiting is applied first, then the lines from the first changed one are
  redrawn once, so a long unmarked paste is not redrawn per key. Widths come from `unicodedata`
  (wide characters 2, combining 0, Tab drawn as 4 spaces). A line that fills its last row exactly
  gets the cursor on a new row, as linenoise does. A move that would take the cursor above the
  screen is not made, since what has scrolled off cannot be redrawn. When the task ends, the
  trailing empty lines are wiped and the status starts on the line below the text. That replaces
  the old `\n` after Ctrl-D and the `ESC[2A` after the empty lines, and `ended_by_empty_lines()` is
  gone.
- Tests: `typed()` in tests/test_route.py now takes the test terminal out of line mode before
  typing, as the keys of a real user arrive while drover reads; `line_mode=True` types them before,
  through the kernel's line editing. New tests cover the editing keys, unknown and malformed
  escape sequences, Enter from mid-text, a marked paste at the cursor with `\r\n`, Ctrl-C, and
  keys typed before drover reads. 27 tests, passing under Python 3.13 and 3.8 (no 3.9 at hand;
  nothing used is newer than 3.8).
- README.md: the paragraph under Use lists the keys.

## Checked

In tmux at 40×30 and 40×12 with an interactive bash, `drover -n --no-model --no-history` and
`read_task()` printing its result:
- a typo fixed with Left and Backspace; End and a line wrapping past 40 columns; Up within the
  wrapped line; Enter, Up, Home, typing; Down, End and Ctrl-W; Ctrl-D, then the route result below
  the text;
- Cyrillic text with Left and Ctrl-W in mid-line, then Enter three times from there: the task
  ended with the text intact;
- `tmux paste-buffer -p` (marked) of `pasted one`, two empty lines, `after two empty`: it did not
  end; two more Enters ended it with the empty lines kept;
- a 40-character line in 40 columns: the cursor went to the next row, and the 41st character went
  there;
- Ctrl-C mid-task: the text stays on screen and KeyboardInterrupt is raised;
- a 20-line paste in a 12-row pane: Up stops at the top row, a character typed there lands in the
  right line, and the result is the full text.

In a herdr tab, through `herdr pane send-text` and `send-keys`, which type raw bytes, not marked
pastes: Left and a fixed typo, Ctrl-A, End, four Ups into the first line, and text sent at once
with two empty lines in it, which did not end the task; Enter then ended it. The tab was closed.

Not checked: macOS, where only the Python version differs here. Routing itself is unchanged, so no
`drover eval` was run.

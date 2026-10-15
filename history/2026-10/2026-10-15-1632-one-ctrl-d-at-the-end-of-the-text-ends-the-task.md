# One Ctrl-D at the end of the text ends the task, and keys pressed while drover works are thrown away

2026-10-15. Follow-up to the entry of 16:16. The owner asked why Ctrl-D had to go on an empty line
and not at the end of the text.

## Why it had to

A terminal in its normal (canonical) mode holds what is typed until a line is done. Ctrl-D hands
over what it holds: after text, that is the text without a newline, and on an empty line it is
nothing, which a program reads as the end. `sys.stdin.read()` keeps reading until it gets that
nothing, so a Ctrl-D after the text only delivered the text, and a second one was needed.

## What changed

- `read_tty()` reads the terminal with `os.read()`. POSIX has the terminal hand over at most one
  line per read, so a chunk that does not end in a newline can only come from Ctrl-D, at the end of
  the text or on a line of its own. The first such chunk ends the task. The prompt and the hint now
  just say "Ctrl-D".
- `drop_typeahead()`, registered with atexit when the task came from a terminal, discards
  (`tcflush`, TCIFLUSH) whatever was typed while drover worked. Pressing Ctrl-D a second time out of
  habit, or Enter while waiting, no longer reaches the shell after drover exits.
- The read_task tests now type into a real pty (`os.openpty`); a new one checks that the text
  after the first Ctrl-D is not read. 19 tests, passing.
- README.md: the hint in the opening example, and the paragraph under Use.

## Checked

In a pty under an interactive bash 5.2, with the real model: `drover -n` and a first line as words,
then a second line with no Enter and a single Ctrl-D. `routing …` showed at once, followed by
`asking the model …` and the result in 1.9 s. During the wait one more Ctrl-D and two Enters were
pressed. The terminal still echoed the two Enters as blank lines, but bash drew one prompt
afterwards, not three.

Routing is unchanged, so no `drover eval` was run.

# Two empty lines end the task, as well as Ctrl-D

2026-10-16. The owner found Ctrl-D awkward to reach for and asked for another way to end a task,
for example Enter pressed three times.

## What changed

- `read_tty()` also ends at two empty lines in a row: Enter three times at the end of the text.
  A one-line task is `drover task text` and three Enters, the first being the one that runs the
  command. Text read from the terminal starts on a line of its own, so two Enters right after the
  hint (or the prompt of a bare `drover`) count as two empty lines (`ended_by_empty_lines()`).
- A paste can hold two empty lines in a row, and ending there would lose the rest, which
  `drop_typeahead()` throws away. A terminal in canonical mode hands over one line per read, so
  when the two empty lines are read, the rest of a paste is already waiting: drover ends the task
  only if nothing more can be read within 0.2 s (`select`). Enter pressed by hand is not that fast,
  and a fourth Enter within 0.2 s just adds an empty line, after which the same check ends it.
  A paste that itself ends in two empty lines ends the task.
- After ending at the empty lines, drover moves the cursor up two lines when stderr is a terminal,
  so the status and the result take the place of the empty lines, as after Ctrl-D.
- Ctrl-D works as before. The hint is now "more lines, or two empty lines or Ctrl-D to route it",
  the prompt of a bare `drover` "Task (finish with two empty lines or Ctrl-D):". README.md (the
  opening example, Use and the notes under it), the usage text, the `task` help, and three new
  unit tests (22 in all, passing).

## Checked

- In a pty, with `-n --no-model`: `drover fix the camera` and then two Enters 0.3 s apart; a bare
  `drover`, a line, and three Enters 0.15 s apart. Both routed, with the status written over the
  empty lines (`ESC[2A`).
- The same with a paste written at once, `pasted line`, two empty lines and one more line: drover
  went on reading and ended at the Ctrl-D that followed.

Routing itself is unchanged, so no `drover eval` was run.

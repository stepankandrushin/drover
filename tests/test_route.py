"""Tests of drover's rules, on a tree of made-up places. Run: python3 -m unittest discover -s tests"""

import importlib.machinery
import io
import os
import shutil
import subprocess
import sys
import tempfile
import termios
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
loader = importlib.machinery.SourceFileLoader("drover", os.path.join(HERE, "..", "drover"))
drover = types.ModuleType(loader.name)
loader.exec_module(drover)


class Tree(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        code = os.path.join(self.root, "code")
        self.files = {
            "code/infra/AGENTS.md": "# infra\n\nServers, routers and the LAN of every site.\n",
            "code/infra/servers/office.md": "x",
            "code/frigate/AGENTS.md": "# Frigate NVR\n\nThe camera recorder.\n",
            "code/web/AGENTS.md": "# AGENTS.md\n\nThis file provides guidance to Claude Code.\n\n"
                                  "## Overview\n\nEvery site driven through a browser.\n",
            "code/web/docs/marketplace.md": "x",
            "code/acme.dev/README.md": "# acme.dev\n\nThe family tree.\n",
            "code/telegram/README.md": "# telegram\n\nA userbot.\n",
            "code/notes/.git/HEAD": "ref: refs/heads/main\n",
            "code/junk.old/README.md": "x",
            "docs/AGENTS.md": "# docs\n\nTax cases.\n",
            "docs/case/next-prompts/2026-10-15-0101-a.md": "x",
        }
        for rel, text in self.files.items():
            path = os.path.join(self.root, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(text)
        os.makedirs(os.path.join(code, "empty"))
        self.ini = os.path.join(self.root, "config.ini")
        with open(self.ini, "w") as f:
            f.write("[drover]\nroots = %s\nplaces = %s\nignore = *.old\ndefault = infra\nhistory_min_score = 1\n\n"
                    "[keywords]\nfrigate = camera, /\\bcam\\d+/\n\n[moved]\n%s = %s\n"
                    % (code, os.path.join(self.root, "docs"), os.path.join(self.root, "old-docs"),
                       os.path.join(self.root, "docs")))
        self.cfg = drover.load_config(self.ini)
        self.places = drover.discover(self.cfg)

    def tearDown(self):
        shutil.rmtree(self.root)

    def history(self, *pairs):
        h = drover.History()
        for task, label in [("restart the router at the house", "infra"), ("the disk on the server is slow", "infra"),
                            ("update the zsh prompt", "notes"), ("rename the tax case folder", "docs")] + list(pairs):
            h.add(task, label)
        return h

    def route(self, task, history=None):
        return drover.route(task, self.places, self.cfg, index=history, use_model=False)

    def test_discover(self):
        names = [p.name for p in self.places]
        self.assertEqual(names, ["acme.dev", "frigate", "infra", "notes", "telegram", "web", "docs"])
        web = drover.by_name(self.places, "web")
        self.assertEqual(web.desc, "Every site driven through a browser.")

    def test_split_list_keeps_commas_in_regex(self):
        self.assertEqual(drover.split_patterns("a, b\n/x{1,2}/, c"), ["a", "b", "/x{1,2}/", "c"])

    def test_explicit(self):
        self.assertEqual(self.route("@web fill the form")["place"], "web")

    def test_path_anchored_beats_other_paths(self):
        d = self.route("Work in %s/code/web; the data is in %s/code/infra/servers/office.md and %s/code/infra"
                       % (self.root, self.root, self.root))
        self.assertEqual((d["place"], d["how"]), ("web", "path"))

    def test_relative_path_that_exists_in_one_place(self):
        d = self.route("look at servers/office.md and fix it")
        self.assertEqual(d["place"], "infra")

    def test_moved_path(self):
        d = self.route("read %s/old-docs/case/x.pdf" % self.root)
        self.assertEqual(d["place"], "docs")

    def test_distinctive_name(self):
        self.assertEqual(self.route("the acme.dev backup is late")["place"], "acme.dev")

    def test_plain_word_name_is_only_a_hint(self):
        d = self.route("send me the result in telegram")
        self.assertNotEqual(d["how"], "name")
        self.assertIn("telegram", " ".join(d["hints"]))

    def test_name_learned_from_history(self):
        h = drover.History()
        for _ in range(3):
            h.add("restart the telegram userbot", "telegram")
        self.assertEqual(self.route("telegram login broke", h)["place"], "telegram")
        h2 = drover.History()
        for _ in range(3):
            h2.add("post it to telegram", "web")
        strong, weak = drover.by_names("telegram login broke", self.places, h2)
        self.assertEqual((strong, weak), ([], ["telegram"]))

    def test_keyword(self):
        self.assertEqual(self.route("cam214 shows a black picture")["place"], "frigate")

    def test_history_decides_alone_when_confident(self):
        h = self.history(*[("answer the marketplace buyer about the shop listing %d" % i, "web") for i in range(5)])
        d = self.route("answer the marketplace buyer about the warehouse listing", h)
        self.assertEqual((d["place"], d["how"]), ("web", "history"))

    def test_conflict_goes_past_the_rules(self):
        h = self.history(*[("answer the marketplace buyer about the shop listing %d" % i, "web") for i in range(5)])
        d = self.route("answer the marketplace buyer about the listing, the plan is in %s/code/infra/servers/office.md"
                       % self.root, h)
        self.assertEqual(d["how"], "guess")  # no model in tests: the first signal, the path

    def test_default(self):
        d = self.route("something nobody has asked before")
        self.assertEqual((d["place"], d["how"]), ("infra", "default"))

    def test_loose_history_label(self):
        p = drover.place_for_path(os.path.join(drover.HOME, "frigate", "x"), self.places, loose=True)
        self.assertEqual(p.name, "frigate")


class Summary(unittest.TestCase):
    def test_skips_boilerplate_and_generic_titles(self):
        text = "# CLAUDE.md\n\nThis file provides guidance to Claude Code (claude.ai/code).\n\n" \
               "## Project Overview\n\nA **bot** that reads [mail](http://x).\n"
        self.assertEqual(drover.summarize(text), "A bot that reads mail.")

    def test_title_and_paragraph(self):
        self.assertEqual(drover.summarize("# omni\n\nA voice page.\nOn demand.\n\n## More\n\nx"),
                         "omni: A voice page. On demand.")


class Pipe(io.StringIO):
    def isatty(self):
        return False


class ReadTask(unittest.TestCase):
    def read(self, words, stdin):
        err, sys.stderr = sys.stderr, io.StringIO()
        try:
            return drover.read_task(words, stdin)
        finally:
            sys.stderr = err

    def typed(self, words, keys, line_mode=False):
        """read_task on a real terminal that the keys were typed into (\x04 is Ctrl-D): typed while
        drover reads, or with line_mode before it starts, when the terminal still edits them."""
        master, slave = os.openpty()
        try:
            if not line_mode:
                mode = termios.tcgetattr(slave)
                mode[0] &= ~termios.ICRNL
                mode[3] &= ~(termios.ICANON | termios.ECHO | termios.ISIG)
                termios.tcsetattr(slave, termios.TCSANOW, mode)
            os.write(master, keys)
            with os.fdopen(slave) as tty:
                return self.read(words, tty)
        finally:
            os.close(master)

    def test_words_then_lines_up_to_ctrl_d_on_a_terminal(self):
        self.assertEqual(self.typed(["fix", "the", "camera"], b"it drops frames\n\n\x04"),
                         "fix the camera\nit drops frames")
        self.assertEqual(self.typed(["fix", "it"], b"\x04"), "fix it")

    def test_one_ctrl_d_at_the_end_of_the_text(self):
        self.assertEqual(self.typed([], b"two\nlines\x04never read\n\x04"), "two\nlines")

    def test_two_empty_lines_end_the_task(self):
        self.assertEqual(self.typed([], b"two\nlines\n\n\n"), "two\nlines")
        self.assertEqual(self.typed(["fix", "it"], b"\n\n"), "fix it")
        self.assertEqual(self.typed(["fix", "it"], b"one empty line\n\n\x04"), "fix it\none empty line")

    def test_empty_lines_inside_a_paste_do_not(self):
        self.assertEqual(self.typed([], b"pasted\n\n\nand more\n\n\n"), "pasted\n\n\nand more")

    def test_keys_edit_the_text(self):
        self.assertEqual(self.typed([], b"fix the camra\033[D\033[De\n\n\n"), "fix the camera")
        self.assertEqual(self.typed([], b"one\ntwo\033[A\001X\033[B\001\177\004"), "Xonetwo")
        self.assertEqual(self.typed([], b"a b c\027\027x\033[D\033[3~y\001\033[Cz\013\004"), "az")
        self.assertEqual(self.typed([], b"one two\033[D\033[D\033[D\025\004"), "two")
        self.assertEqual(self.typed([], b"a\033[15~b\033[1;2Pc\033[\033[Cd\004"), "abcd")

    def test_enter_starts_a_line_at_the_end_wherever_the_cursor_is(self):
        self.assertEqual(self.typed([], b"fix it\033[D\033[D\n\n\n"), "fix it")
        self.assertEqual(self.typed([], b"one\033[Dx\ntwo\004"), "onxe\ntwo")

    def test_a_paste_goes_in_at_the_cursor(self):
        self.assertEqual(self.typed([], b"ab\033[D\033[200~1\r\n\n2\033[201~\004"), "a1\n\n2b")

    def test_typed_before_drover_reads(self):
        self.assertEqual(self.typed(["fix", "it"], b"more\x04", line_mode=True), "fix it\nmore")
        self.assertEqual(self.typed([], b"two\nlines\x04never read\n\x04", line_mode=True), "two\nlines")

    def test_ctrl_c(self):
        with self.assertRaises(KeyboardInterrupt):
            self.typed([], b"half a task\003")

    def test_words_alone_from_a_pipe(self):
        self.assertEqual(self.read(["--", "fix", "-n"], Pipe("not read\n")), "fix -n")
        self.assertEqual(self.read([], Pipe("piped task\n")), "piped task")


class RunHere(unittest.TestCase):
    def test_the_shell_function_cds_and_runs_the_line(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root)
        place, out = os.path.join(root, "it's a place"), os.path.join(root, "run")
        os.mkdir(place)
        os.environ["DROVER_RUN_FILE"] = out
        try:
            drover.run_here(place, "pwd -P")
        finally:
            del os.environ["DROVER_RUN_FILE"]
        r = subprocess.run(["sh", "-c", 'cd /; eval "$(cat "$1")"', "sh", out], capture_output=True, text=True)
        self.assertEqual(r.stdout.strip(), os.path.realpath(place))


if __name__ == "__main__":
    unittest.main()

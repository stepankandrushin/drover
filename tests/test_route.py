"""Tests of drover's rules, on a tree of made-up places. Run: python3 -m unittest discover -s tests"""

import importlib.machinery
import os
import shutil
import tempfile
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


if __name__ == "__main__":
    unittest.main()

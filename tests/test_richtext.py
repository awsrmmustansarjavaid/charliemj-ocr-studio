"""Unit tests for app/richtext.py (document model + exporters). No GUI, no OCR."""
import os
import tempfile
import unittest
import xml.dom.minidom
import zipfile

from app.richtext import (Block, Run, blocks_pairs, blocks_to_html, blocks_to_md, blocks_to_text,
                          md_to_blocks, write_docx)

NOTES = "# Main title\n### Sub\n## Vocabulary\n- **gamze** — dimple\n- **ben** — mole\n---\nPlain *line*"


class RichTextTests(unittest.TestCase):
    def test_markdown_becomes_styled_blocks(self):
        b = md_to_blocks(NOTES)
        self.assertEqual([x.style for x in b[:3]], ["h1", "h3", "h2"])
        self.assertTrue(b[3].is_bullet and b[3].runs[1].bold)
        self.assertTrue(b[5].hr)

    def test_table_becomes_bullets(self):
        md = "|  # | Turkish | English |\n|----|---|---|\n|  1 | kedi | cat |\n|  2 | köpek | dog |"
        b = md_to_blocks(md)
        self.assertEqual([x.text for x in b], ["• kedi — cat", "• köpek — dog"])

    def test_markdown_roundtrip(self):
        md = blocks_to_md(md_to_blocks(NOTES, top="title"))
        self.assertIn("# Main title", md)
        self.assertIn("- **gamze** — dimple", md)

    def test_plain_text_and_pairs(self):
        blocks = [Block("title", runs=[Run("Image 2")])] + md_to_blocks("- **gamze** — dimple")
        self.assertEqual(blocks_pairs(blocks), [(2, "gamze", "dimple")])
        self.assertIn("• gamze — dimple", blocks_to_text(blocks))

    def test_html_groups_bullets(self):
        h = blocks_to_html(md_to_blocks(NOTES))
        self.assertEqual(h.count("<ul>"), 1)
        self.assertIn("<li><span", h)

    def test_docx_is_valid_zip_with_xml(self):
        blocks = md_to_blocks(NOTES) + [Block(runs=[Run("renk", color="#ff0000", bg="#ffff00", size=20, underline=True)])]
        path = os.path.join(tempfile.mkdtemp(), "x.docx")
        write_docx(path, blocks)
        with zipfile.ZipFile(path) as z:
            self.assertEqual(sorted(z.namelist()), ["[Content_Types].xml", "_rels/.rels", "word/document.xml"])
            for n in z.namelist():
                xml.dom.minidom.parseString(z.read(n))       # every part is well-formed XML
            self.assertIn("gamze", z.read("word/document.xml").decode("utf-8"))


if __name__ == "__main__":
    unittest.main()

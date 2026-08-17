# -*- coding: utf-8 -*-
"""解析器的单元测试。测试纯逻辑，不需要网络。"""
import unittest

from scout.parser import parse_readme

SAMPLE = """# Public APIs

## Index
* [Animals](#animals)
* [Weather](#weather)

### Animals
API | Description | Auth | HTTPS | CORS
|:---|:---|:---|:---|:---|
| [Cat Facts](https://catfact.ninja/) | Random cat facts | No | Yes | Yes |
| [Dogs](https://dog.ceo/dog-api/) | Based on the Stanford Dogs Dataset | No | Yes | Yes |

### Weather
| [Open-Meteo](https://open-meteo.com/) | Global weather forecast API | No | Yes | Unknown |
"""


class TestParser(unittest.TestCase):

    def test_entry_count(self):
        entries = parse_readme(SAMPLE)
        self.assertEqual(len(entries), 3)

    def test_fields_parsed(self):
        e = parse_readme(SAMPLE)[0]
        self.assertEqual(e.name, "Cat Facts")
        self.assertEqual(e.url, "https://catfact.ninja/")
        self.assertEqual(e.category, "Animals")
        self.assertEqual(e.auth, "No")
        self.assertEqual(e.cors, "Yes")
        self.assertEqual(e.line, 10)

    def test_category_tracking(self):
        entries = parse_readme(SAMPLE)
        self.assertEqual(entries[2].category, "Weather")

    def test_skips_header_and_separator(self):
        entries = parse_readme(SAMPLE)
        names = [e.name for e in entries]
        self.assertNotIn("API", names)
        self.assertTrue(all(e.name not in (":---", "---") for e in entries))

    def test_handles_sixth_column(self):
        # 新版格式允许追加 "Call this API" 列
        text = "### X\n| [A](https://a.b) | desc | No | Yes | Yes | [Postman](https://p.b) |\n"
        entries = parse_readme(text)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].auth, "No")
        self.assertEqual(entries[0].url, "https://a.b")

    def test_strips_backticks_from_auth(self):
        text = "### X\n| [A](https://a.b) | desc | `apiKey` | Yes | Yes |\n"
        entries = parse_readme(text)
        self.assertEqual(entries[0].auth, "apiKey")

    def test_empty_input(self):
        self.assertEqual(parse_readme(""), [])


if __name__ == "__main__":
    unittest.main()

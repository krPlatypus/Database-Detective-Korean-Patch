"""게임 없이 확인할 수 있는 번역 번들 회귀 검사."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import build_translation as builder


class TranslationBuildTests(unittest.TestCase):
    def test_format_handles_reordered_repeated_placeholders_and_literal_dollars(self):
        result = builder.format_pattern('Error {0}: {1} ({0})', '{1}: {0}, $5')
        self.assertIn(r'\k<arg0>', result['match'])
        self.assertEqual(result['replace'], '${arg1}: ${arg0}, $$5')
        self.assertTrue(result['match'].startswith('^Error'))
        self.assertTrue(result['match'].endswith('$'))

    def test_missing_placeholder_rejected(self):
        with self.assertRaises(ValueError):
            builder.format_pattern('Error {0}: {1}', '오류 {0}')

    def test_relocated_asset_uses_content_not_recycled_id(self):
        old = {'name': 'correct', 'source': 'resources.assets:1', 'sha256': builder.source_hash('first case')}
        records = [{'name': 'correct', 'source': 'resources.assets:1', 'text': 'different case'},
                   {'name': 'correct', 'source': 'resources.assets:2', 'text': 'first case'}]
        self.assertEqual(builder.resolve_original(old, records), 'first case')
        records.pop()
        with self.assertRaises(ValueError):
            builder.resolve_original(old, records)

    def test_wrong_name_rejected_even_when_id_matches(self):
        with self.assertRaises(ValueError):
            builder.resolve_original({'name': 'correct', 'source': 'assets:1'},
                                     [{'name': 'wrong', 'source': 'assets:1', 'text': 'wrong case'}])

    def test_build_combines_formats_and_current_asset_without_extract_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            translation = root / 'translation'
            assets = translation / 'textassets'
            assets.mkdir(parents=True)
            (translation / 'ui.json').write_text('{"Open": "열기", "movies": ""}', encoding='utf-8')
            (translation / 'dynamic.json').write_text('{"Flight #{0}": "항공편 #{0}"}', encoding='utf-8')
            (translation / 'patterns.json').write_text('[{"match":"^manual$","replace":"manual"}]', encoding='utf-8')
            (assets / 'line.txt').write_text('현재 대사', encoding='utf-8')
            manifest = {'line.txt': {'name': 'intro', 'source': 'old:1', 'sha256': builder.source_hash('current script')}}
            (assets / '_manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
            with patch.object(builder, 'TRANSLATION', str(translation)), patch.object(builder, 'DIST', str(root / 'dist')):
                output = builder.build([{'name': 'intro', 'source': 'new:5', 'text': 'current script'}])
            bundle = json.loads(Path(output).read_text(encoding='utf-8'))
            self.assertEqual(bundle['textAssets'], {'current script': '현재 대사'})
            self.assertNotIn('movies', bundle['ui'])
            self.assertEqual(bundle['patterns'][0]['match'], '^manual$')
            self.assertIn('arg0', bundle['patterns'][1]['match'])

    def test_repository_exclusions_are_not_exactly_translated(self):
        root = Path(__file__).resolve().parent.parent / 'translation'
        exact = {}
        for name in ('ui', 'dynamic'):
            exact.update({k: v for k, v in json.loads((root / f'{name}.json').read_text(encoding='utf-8')).items() if v.strip()})
        for name in ('ui_keep_original', 'code_strings_skipped'):
            for source in json.loads((root / f'{name}.json').read_text(encoding='utf-8')):
                self.assertEqual(exact.get(source, source), source, source)


if __name__ == '__main__':
    unittest.main()

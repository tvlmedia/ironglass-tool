import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
spec = importlib.util.spec_from_file_location('discover', Path(__file__).resolve().parents[1] / 'scripts/discover.py')
d = importlib.util.module_from_spec(spec); spec.loader.exec_module(d)

class DiscoveryTests(unittest.TestCase):
    def test_only_explicit_brand_on_imdb_title(self):
        valid = {'url': 'https://www.imdb.com/title/tt12345/technical/', 'title': 'Example (2024) - Technical specifications - IMDb', 'description': 'Alexa, Iron Glass Helios lenses'}
        row = d.extract(valid, 'query', 'test')
        self.assertEqual(row['id'], 'tt12345')
        self.assertEqual(row['sourceKind'], 'Lensspecificaties')
        for change in [{'url':'https://evil.example/title/tt12345/'}, {'url':'https://www.imdb.com/list/ls12345/'}, {'description':'Helios lenses'}, {'description':'IronGlassware products'}]:
            self.assertIsNone(d.extract({**valid, **change}, 'q', 'test'))
    def test_localized_company_source_and_type(self):
        row = d.extract({'url':'https://www.imdb.com/fr/title/tt12345/companycredits/?ref_=x','title':'Example (Music Video 2025) - Company credits - IMDb','description':'IronGlass: camera equipment'}, 'q', 'test')
        self.assertEqual(row['type'], 'Music video')
        self.assertTrue(row['url'].endswith('/companycredits/'))
    def test_blocking_preserves_existing_and_reports_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); records=[{'id':'tt1', 'title':'Existing', 'status':'Gecontroleerd'}]
            (root/'results.json').write_text(json.dumps(records))
            with patch.object(d, 'provider_search', side_effect=d.Blocked('blocked')), patch.dict('os.environ', {}, clear=True):
                report=d.run(root, limit=2, delay=0)
            self.assertEqual(report['state'], 'blocked')
            self.assertEqual(json.loads((root/'results.json').read_text()), records)
            self.assertEqual(report['requestsSucceeded'], 0)
    def test_duplicates_and_unverified_status(self):
        row={'url':'https://www.imdb.com/title/tt12345/fullcredits/', 'title':'Example (2024) - IMDb', 'description':'IronGlass: lenses'}
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'results.json').write_text('[]')
            with patch.object(d,'provider_search',return_value=[row,row]),patch.dict('os.environ',{},clear=True):
                report=d.run(root,limit=2,delay=0)
            data=json.loads((root/'results.json').read_text())
            self.assertEqual(report['newTitles'],1)
            self.assertEqual(len(data),1)
            self.assertEqual(data[0]['status'],'Kandidaat')
    def test_query_rotation(self):
        common,extra=d.query_plan(2026)
        self.assertTrue(any('1990' in q for q in extra))
        self.assertTrue(any('2027' in q for q in extra))
        self.assertTrue(any('company credits' in q for q in common))

if __name__=='__main__':unittest.main()

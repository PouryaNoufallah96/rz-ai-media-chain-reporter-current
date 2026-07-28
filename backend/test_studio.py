import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database
from handlers import studio
from video_pipeline import assemble_video_prompt, validate_script_facts


class StudioTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = database.DB_PATH
        self.original_output_dir = studio.STUDIO_OUTPUT_DIR
        database.DB_PATH = Path(self.temp_dir.name) / 'studio-test.db'
        studio.STUDIO_OUTPUT_DIR = Path(self.temp_dir.name) / 'output'
        studio._model_cache.update({'at': 0.0, 'models': []})
        database.init_db()
        self.user_one = database.create_user('studio-one', 'one@example.com', 'hash')['id']
        self.user_two = database.create_user('studio-two', 'two@example.com', 'hash')['id']
        self.cards = [{
            'id': 'story-1',
            'media': 'ChainReporter',
            'headline': 'Bitcoin market structure shifts after institutional demand',
            'copy': 'Institutional demand changed the market structure according to the selected report.',
            'source': 'Example News',
            'link': 'https://example.com/story',
        }]
        self.settings = {
            'duration': 30,
            'resolution': '720p',
            'model': 'google/veo-3.1',
            'voice': 'News Anchor',
            'music': 'Market Pulse',
            'language': 'English',
            'generateAudio': True,
        }
        self.script = {
            'hook': 'A market shift is underway',
            'narration': 'Institutional demand is changing Bitcoin market structure.',
            'shots': [{'start': '0s', 'end': '30s', 'visual': 'Bitcoin market graphics', 'caption': 'Market structure shifts'}],
            'on_screen_captions': ['Market structure shifts'],
            'cta': 'Follow for the next update.',
            'hashtags': ['#Bitcoin'],
            'video_prompt': 'A credible newsroom reel with clean market graphics.',
            'directorBrief': {
                'format': 'mechanism_reveal',
                'visualConcept': 'An abstract financial mechanism revealing a shift in market structure.',
                'heroObject': 'transparent mechanism',
                'palette': 'black, graphite, and mint highlights',
                'camera': 'controlled orbit',
                'motionArc': ['Introduce a symbolic asset.', 'Reveal the structural relationship.', 'Resolve on a calm tableau.'],
                'negativeConstraints': 'No logos or watermarks.',
                'rationale': 'A mechanism reveal fits the source.',
            },
        }

    def _models_response(self):
        return {'data': [{
            'id': 'google/veo-3.1',
            'name': 'Google: Veo 3.1',
            'supported_aspect_ratios': ['16:9', '9:16'],
            'supported_resolutions': ['720p'],
            'supported_durations': [8, 30],
            'generate_audio': True,
            'pricing_skus': {'per-video-second': '0.50'},
        }]}

    def tearDown(self):
        database.DB_PATH = self.original_db_path
        studio.STUDIO_OUTPUT_DIR = self.original_output_dir
        studio._model_cache.update({'at': 0.0, 'models': []})
        self.temp_dir.cleanup()

    def test_drafts_and_jobs_are_isolated_per_user(self):
        draft = studio.handle_studio_draft(self.user_one, {
            'cards': self.cards,
            'settings': self.settings,
        })['draft']
        self.assertIsNotNone(database.get_studio_draft(draft['id'], self.user_one))
        self.assertIsNone(database.get_studio_draft(draft['id'], self.user_two))
        with self.assertRaisesRegex(ValueError, 'not found'):
            studio.handle_studio_draft(self.user_two, {
                'draftId': draft['id'],
                'cards': self.cards,
                'settings': self.settings,
            })
        self.assertEqual(studio.handle_studio_jobs(self.user_two)['jobs'], [])

    @patch('handlers.studio.openrouter_video_models')
    def test_model_discovery_returns_only_vertical_models(self, discover):
        discover.return_value = {'data': [
            {
                'id': 'google/veo-3.1',
                'name': 'Google: Veo 3.1',
                'supported_aspect_ratios': ['16:9', '9:16'],
                'supported_resolutions': ['720p'],
                'supported_durations': [8, 30],
                'generate_audio': True,
                'supported_frame_images': ['first_frame'],
                'pricing_skus': {'per-video-second': '0.50'},
            },
            {
                'id': 'landscape/only',
                'name': 'Landscape only',
                'supported_aspect_ratios': ['16:9'],
                'supported_resolutions': ['720p'],
            },
        ]}
        result = studio.handle_studio_models()
        self.assertEqual([model['id'] for model in result['models']], ['google/veo-3.1'])
        self.assertEqual(result['models'][0]['pricePerSecond'], '0.50')
        self.assertEqual(result['models'][0]['durations'], [8, 30])
        self.assertTrue(result['models'][0]['generateAudio'])

    @patch('handlers.studio.openrouter_video_models')
    def test_model_discovery_preserves_a_useful_upstream_error(self, discover):
        discover.side_effect = ValueError('OpenRouter video model discovery failed (503): unavailable')
        with self.assertRaisesRegex(ValueError, 'model discovery failed'):
            studio.handle_studio_models()

    @patch('handlers.studio.openrouter_video_content')
    @patch('handlers.studio.openrouter_video_poll')
    @patch('handlers.studio.openrouter_video_submit')
    @patch('handlers.studio.openrouter_video_models')
    def test_submit_poll_and_download_completed_reel(self, discover, submit, poll, content):
        discover.return_value = self._models_response()
        submit.return_value = {
            'id': 'provider-job-123',
            'polling_url': 'https://openrouter.ai/api/v1/videos/provider-job-123',
            'status': 'pending',
        }
        poll.return_value = {
            'id': 'provider-job-123',
            'status': 'completed',
            'unsigned_urls': ['https://openrouter.ai/api/v1/videos/provider-job-123/content?index=0'],
            'usage': {'cost': 1.25},
        }
        content.return_value = (b'fake-mp4-content', 'video/mp4')

        generated = studio.handle_studio_generate(self.user_one, {
            'cards': self.cards,
            'settings': self.settings,
            'script': self.script,
        })
        job = generated['job']
        self.assertEqual(job['status'], 'pending')
        self.assertEqual(studio.handle_studio_jobs(self.user_two)['jobs'], [])

        completed = studio.handle_studio_poll(self.user_one, {'id': job['id']})['job']
        self.assertEqual(completed['status'], 'completed')
        self.assertTrue(completed['hasLocalVideo'])
        self.assertEqual(completed['cost'], 1.25)

        download = studio.handle_studio_download(self.user_one, job['id'])
        self.assertEqual(download['path'].read_bytes(), b'fake-mp4-content')
        self.assertEqual(download['contentType'], 'video/mp4')
        with self.assertRaisesRegex(ValueError, 'not found'):
            studio.handle_studio_download(self.user_two, job['id'])

    @patch('handlers.studio.openrouter_video_models')
    def test_generate_requires_reviewed_direction(self, discover):
        discover.return_value = self._models_response()
        script = {key: value for key, value in self.script.items() if key != 'directorBrief'}
        with self.assertRaisesRegex(ValueError, 'Create and review art direction'):
            studio.handle_studio_generate(self.user_one, {
                'cards': self.cards,
                'settings': self.settings,
                'script': script,
            })

    def test_fact_boundary_rejects_unknown_numeric_claims(self):
        script = {**self.script, 'narration': 'Bitcoin will reach 900000 tomorrow.'}
        with self.assertRaisesRegex(ValueError, 'figures not present'):
            validate_script_facts(script, self.cards)

    def test_editorial_house_style_is_compiled_into_provider_prompt(self):
        prompt = assemble_video_prompt(
            self.script,
            self.script['directorBrief'],
            self.settings,
            self.cards,
        )
        self.assertIn('VISUAL SYSTEM: Minimal Signal Thesis.', prompt)
        self.assertIn('Reserve the upper third as quiet negative space', prompt)
        self.assertIn('Do not use stock footage, generic crypto b-roll', prompt)


if __name__ == '__main__':
    unittest.main()

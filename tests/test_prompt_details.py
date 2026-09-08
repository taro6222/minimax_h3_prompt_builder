import importlib.util
import json
from pathlib import Path
import unittest


spec = importlib.util.spec_from_file_location("h3_builder", Path(__file__).resolve().parents[1] / "__init__.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class PromptDetailsTests(unittest.TestCase):
    def setUp(self):
        self.node = builder.MiniMaxH3RefPromptBuilder
        self.inputs = {field.id: field.options[0] for field in self.node.define_schema().inputs if hasattr(field, "options")}

    def generate(self, fields, duration=5, **inputs):
        return self.node.execute(**(self.inputs | inputs), prompt_details=json.dumps({"duration": duration, "fields": fields})).result[0]

    def test_action_interval_and_text_remain_in_shot(self):
        prompt = self.generate({"action": {"start": 1, "end": 3, "prompt": "Use the right hand."}}, action="인물 · 손 흔들기")
        detail = prompt.split("detailed_description:\n")[1].split("\n\noverall_soundscape:")[0]
        self.assertIn("from 1.000 to 3.000 seconds", detail)
        self.assertIn("Use the right hand.", detail)
        self.assertIn("waves it gently", detail)
        self.assertIn("target duration is 5 seconds", prompt)

    def test_camera_and_music_reference_keep_details(self):
        prompt = self.generate({
            "camera": {"start": 1, "end": 4, "prompt": "Keep the horizon level."},
            "music": {"start": 2, "end": 5, "prompt": "Use a quiet ending."},
        }, camera_source="<Video 2>", music_source="<Audio 3>")
        self.assertIn("Camera movement applies from 1.000 to 4.000 seconds", prompt)
        self.assertIn("pace of <Video 2>", prompt)
        self.assertIn("Keep the horizon level.", prompt)
        self.assertNotIn("accompanies the shot from its opening", prompt)
        score = prompt.split("non_diegetic_music:\n")[1]
        self.assertIn("from 2.000 to 5.000 seconds", score)
        self.assertIn("<Audio 3>", score)
        self.assertIn("Use a quiet ending.", score)

    def test_description_routing(self):
        prompt = self.generate({
            "subject_kind": {"prompt": "Wearing a blue jacket."},
            "background_source": {"prompt": "A narrow garden path."},
            "soundscape": {"start": 0, "end": 2, "prompt": "Leaves rustle softly."},
        })
        self.assertIn("Wearing a blue jacket.", prompt.split("\n\nsummary:")[0])
        self.assertIn("A narrow garden path.", prompt.split("detailed_description:")[1])
        self.assertIn("Leaves rustle softly.", prompt.split("overall_soundscape:")[1])

    def test_invalid_intervals(self):
        for start, end in [(-1, 2), (2, 2), (3, 1), (0, 6), (True, 2), (None, 2), (0, float("nan")), (0, float("inf"))]:
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                self.generate({"action": {"start": start, "end": end}})
        with self.assertRaises(ValueError):
            self.generate({"style": {"start": 0, "end": 2}})
        with self.assertRaises(ValueError):
            self.generate({"action": {"start": 0}})

    def test_invalid_settings(self):
        for settings in ["null", "[]", "{", '{"fields": []}', '{"fields": {"unknown": {}}}', '{"fields": {"action": {"prompt": 5}}}', '{"duration": null}']:
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                self.node.execute(**self.inputs, prompt_details=settings)

    def test_clothing_replacement_and_world_retention(self):
        prompt = self.generate({"clothing": {"prompt": "A blue silk robe."}},
                               clothing="다른 옷 · 직접 지정", era="마법의 세계", background_source="<Picture 2>")
        self.assertIn("A blue silk robe.", prompt)
        self.assertIn("magical fantasy world", prompt)
        retention = prompt.split("retention_analysis:\n")[1].split("\n\ndetailed_description:")[0]
        self.assertNotIn("fully_preserved", retention)
        self.assertIn("replacing clothing", retention)
        self.assertIn("adapting architecture", retention)
        with self.assertRaises(ValueError):
            self.generate({}, clothing="다른 옷 · 직접 지정")

    def test_new_defaults_and_old_widget_order(self):
        old = {key: value for key, value in self.inputs.items() if key not in ("clothing", "era")}
        self.assertEqual(self.node.execute(**old).result, self.node.execute(**self.inputs).result)
        names = [field.id for field in self.node.define_schema().inputs]
        self.assertEqual(names[-3:], ["prompt_details", "clothing", "era"])
        prompt = self.generate({})
        self.assertIn("original clothing and accessories unchanged", prompt)
        self.assertIn("fully_preserved", prompt)

    def test_all_new_presets_and_extra_descriptions(self):
        for name, (_, options) in builder.EXTRA_OPTIONS.items():
            for option, phrase in options.items():
                with self.subTest(name=name, option=option):
                    prompt = self.generate({name: {"prompt": "Custom detail."}}, **{name: option})
                    self.assertIn(phrase, prompt)
                    self.assertIn("Custom detail.", prompt)
        with self.assertRaises(ValueError):
            self.generate({"era": {"start": 0, "end": 3}})

    def test_default_api_call_and_serialized_roundtrip(self):
        self.assertEqual(self.node.execute(**self.inputs).result, self.node.execute(**self.inputs, prompt_details="{}").result)
        raw = json.dumps({"fields": {"action": {"prompt": "Wait, then wave.", "start": 1, "end": 4}}, "duration": 5})
        self.assertEqual(self.node.execute(**self.inputs, prompt_details=raw).result,
                         self.node.execute(**self.inputs, prompt_details=json.loads(json.dumps(raw))).result)


if __name__ == "__main__":
    unittest.main()

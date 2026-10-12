"""Source-level integration checks without opening real audio devices."""
import ast
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class Control:
    def update(self, **kwargs):
        self.values = kwargs

class Source:
    def __init__(self):
        self.sessions = [('23', 'player.exe', 'Player')]
    def enumerate(self):
        return self.sessions
    def resolve(self, identity):
        return 23 if identity == 'player.exe' else 0

class Tests(unittest.TestCase):
    def test_history_survives_missing_session(self):
        for variant in ('cu118', 'cu128'):
            source = ROOT / ('RVC-Realtime-GUI_' + variant) / 'app/realtime_gui.py'
            if not source.exists():
                source = ROOT / 'app/realtime_gui.py'
            tree = ast.parse(source.read_text(encoding='utf-8'))
            method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'refresh_applications')
            namespace = {'IS_JAPANESE_UI': False}
            exec(compile(ast.Module(body=[method], type_ignores=[]), '<refresh>', 'exec'), namespace)
            class GUI:
                application_source = Source()
                application_history = {}
                selected_application = ''
                window = {'application_choice': Control()}
                def save_config_updates(self, data):
                    self.saved = data
            gui = GUI()
            refresh = namespace['refresh_applications']
            refresh(gui)
            self.assertEqual(gui.selected_application, 'player.exe')
            gui.application_source.sessions = []
            refresh(gui)
            self.assertEqual(len(gui.application_choices), 1)
            self.assertEqual(next(iter(gui.application_choices.values())), ('player.exe', 23))
            self.assertEqual(gui.saved['application_history'], {'player.exe': 'Player'})

if __name__ == '__main__':
    unittest.main()

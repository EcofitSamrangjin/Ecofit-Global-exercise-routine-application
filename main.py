from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
import json
import os
import sys
from datetime import datetime
from kivy.core.text import LabelBase

def resource_path(relative_path):
    """EXE와 같은 위치에서 파일 참조"""
    base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.join(base_dir, relative_path)

def get_data_path(filename):
    """PyInstaller exe에서도 안전하게 저장 가능한 경로 반환"""
    if hasattr(sys, '_MEIPASS'):
        # AppData/Local/Ecofit 폴더에 저장
        base_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Ecofit")
        if not os.path.exists(base_dir):
            os.makedirs(base_dir, exist_ok=True)
        return os.path.join(base_dir, filename)
    else:
        # 개발 단계에서는 현재 폴더 사용
        return filename

# -------------------- FILE PATHS --------------------
FONT_FILE = resource_path("NotoSansKR-VariableFont_wght.ttf")
SAVE_FILE = get_data_path("workout_data.json")     # 데이터는 사용자 폴더에 저장
RECORD_FILE = get_data_path("workout_records.json")
LANG_FILE = get_data_path("languages/language.json")

# 폰트 등록 (없으면 예외날 수 있음 — 필요 없으면 주석 처리 가능)
try:
    LabelBase.register(name="NotoSans", fn_regular=FONT_FILE)
except Exception:
    # 폰트 파일이 없으면 기본 폰트로 계속 동작
    pass

# -------------------- 번역 파일 유틸 --------------------
def load_language_setting():
    if os.path.exists(LANG_FILE):
        try:
            with open(LANG_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get("lang", "ko")
        except Exception:
            return "ko"
    return "ko"

def save_language_setting(lang):
    try:
        with open(LANG_FILE, "w", encoding="utf-8") as f:
            json.dump({"lang": lang}, f)
    except Exception:
        pass

def load_translation(lang):
    path = resource_path(f"languages/{lang}.json")  # 언어 폴더 안으로 경로 변경
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {}

# -------------------- 커스텀 위젯 --------------------
class FLabel(Label):
    def __init__(self, **kwargs):
        kwargs.setdefault("font_name", "NotoSans")
        super().__init__(**kwargs)

class FButton(Button):
    def __init__(self, **kwargs):
        kwargs.setdefault("font_name", "NotoSans")
        super().__init__(**kwargs)

class FTextInput(TextInput):
    def __init__(self, **kwargs):
        kwargs.setdefault("font_name", "NotoSans")
        super().__init__(**kwargs)


# -------------------- 메인 앱 --------------------
class WorkoutApp(App):

    def tr(self, key):
        return self.translations.get(key, key)

    def restart_ui(self):
        """언어 변경 후 UI 전체 재구성"""
        new_root = self._build_root_layout()
        self.root.clear_widgets()
        self.root.add_widget(new_root)
        self.root_layout = new_root
    def show_language_toggle(self, instance):
        """언어 선택 버튼 토글"""
        # 이미 표시 중이면 제거
        if hasattr(self, "_lang_box") and self._lang_box.parent:
            self.root_layout.remove_widget(self._lang_box)
            return

        # 새로 생성
        self._lang_box = BoxLayout(orientation='vertical', spacing=5, size_hint_y=None)
        self._lang_box.height = 50 * 10  # 10개 언어
        langs = ["ko", "en", "ja", "zh", "zh-tw", "es", "fr", "de", "ru", "ar"]
        names = ["한국어", "English", "日本語", "简体中文", "繁體中文", "Español", "Français", "Deutsch", "Русский",
                 "العربية"]

        for code, name in zip(langs, names):
            btn = FButton(text=name, size_hint_y=None, height=50)
            btn.bind(on_release=lambda x, c=code: self.change_language(c))
            self._lang_box.add_widget(btn)

        self.root_layout.add_widget(self._lang_box)

    def change_language(self, lang):
        save_language_setting(lang)
        self.lang = lang
        self.translations = load_translation(lang)
        # toggle 패널 제거
        if hasattr(self, "_lang_box") and self._lang_box.parent:
            self.root_layout.remove_widget(self._lang_box)
        self.restart_ui()

    def select_language(self, lang):
        save_language_setting(lang)
        self.lang = lang
        self.translations = load_translation(lang)
        if hasattr(self, "lang_toggle") and self.lang_toggle.parent:
            self.root_layout.remove_widget(self.lang_toggle)
        Clock.schedule_once(lambda dt: self.restart_ui(), 0.05)

    def build(self):
        # 언어 로딩
        self.lang = load_language_setting()
        self.translations = load_translation(self.lang)

        # 데이터 로드
        self.routines = self.load_data()
        self.records = self.load_records()

        # root layout 생성 (분리된 함수로 재사용 가능)
        self.root_layout = self._build_root_layout()
        return self.root_layout

    def _build_root_layout(self):
        root_layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        self.title_label = FLabel(text=self.tr("app_title"), font_size=28, size_hint_y=None, height=50)
        root_layout.add_widget(self.title_label)

        self.scroll = ScrollView(size_hint=(1, 1))
        self.routine_list = BoxLayout(orientation='vertical', spacing=5, size_hint_y=None)
        self.routine_list.bind(minimum_height=self.routine_list.setter('height'))
        self.scroll.add_widget(self.routine_list)
        root_layout.add_widget(self.scroll)
        self.refresh_routine_list()

        add_btn = FButton(text=self.tr("add_routine"), size_hint_y=None, height=50, on_release=self.show_add_routine_popup)
        root_layout.add_widget(add_btn)

        rec_btn = FButton(text=self.tr("records"), size_hint_y=None, height=50, on_release=self.show_records)
        root_layout.add_widget(rec_btn)

        # 언어 버튼
        lang_btn = FButton(text=self.lang.upper(), size_hint_y=None, height=50)
        lang_btn.bind(on_release=self.show_language_toggle)
        root_layout.add_widget(lang_btn)

        return root_layout

    # -------------------- ROUTINE MANAGEMENT --------------------
    def refresh_routine_list(self):
        self.routine_list.clear_widgets()
        if not self.routines:
            self.routine_list.add_widget(FLabel(text=self.tr("no_routine"), size_hint_y=None, height=30))
        else:
            for name in self.routines.keys():
                btn_layout = BoxLayout(size_hint_y=None, height=50)
                btn = FButton(text=name)
                btn.bind(on_release=lambda instance, n=name: self.open_routine(n))
                delete_btn = FButton(text=self.tr("delete_short"), size_hint_x=None, width=50)
                delete_btn.bind(on_release=lambda instance, n=name: self.delete_routine(n))
                btn_layout.add_widget(btn)
                btn_layout.add_widget(delete_btn)
                self.routine_list.add_widget(btn_layout)

    def delete_routine(self, name):
        if name in self.routines:
            del self.routines[name]
            self.save_data()
            self.refresh_routine_list()

    def show_add_routine_popup(self, instance):
        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        name_input = FTextInput(hint_text=self.tr("routine_name"), size_hint_y=None, height=40)
        layout.add_widget(name_input)
        desc_input = FTextInput(hint_text=self.tr("description"), size_hint_y=None, height=80)
        layout.add_widget(desc_input)

        popup_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        ok_btn = FButton(text=self.tr("yes"))
        cancel_btn = FButton(text=self.tr("no"))
        popup_layout.add_widget(ok_btn)
        popup_layout.add_widget(cancel_btn)
        layout.add_widget(popup_layout)

        popup = Popup(title=self.tr("add_routine"), content=layout, size_hint=(0.7, 0.5), auto_dismiss=False, title_font="NotoSansKR-VariableFont_wght.ttf")

        def create_routine(instance):
            name = name_input.text.strip()
            desc = desc_input.text.strip()
            if not name or name in self.routines:
                return
            self.routines[name] = {"description": desc, "exercises": []}
            self.save_data()
            popup.dismiss()
            self.refresh_routine_list()

        ok_btn.bind(on_release=create_routine)
        cancel_btn.bind(on_release=popup.dismiss)
        popup.open()

    # -------------------- ROUTINE DETAIL --------------------
    def open_routine(self, routine_name):
        self.root_layout.clear_widgets()
        self.current_routine = routine_name
        data = self.routines[routine_name]

        title = FLabel(text=f"[b]{routine_name}[/b]", markup=True, font_size=26, size_hint_y=None, height=50)
        self.root_layout.add_widget(title)
        # 저장은 'description' 키에 하므로 보여줄 때도 'description' 사용
        desc_label = FLabel(text=data.get("description", ""), size_hint_y=None, height=50)
        self.root_layout.add_widget(desc_label)

        self.scroll_ex = ScrollView(size_hint=(1, 1))
        self.exercise_box = BoxLayout(orientation='vertical', spacing=5, size_hint_y=None)
        self.exercise_box.bind(minimum_height=self.exercise_box.setter('height'))
        self.scroll_ex.add_widget(self.exercise_box)
        self.root_layout.add_widget(self.scroll_ex)

        self.refresh_exercise_list(data)

        btn_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        add_ex_btn = FButton(text=self.tr("add_exercise"), on_release=self.show_add_exercise_popup)
        run_btn = FButton(text=self.tr("run_routine"), on_release=self.show_routine_type_popup)
        back_btn = FButton(text=self.tr("back"), on_release=self.go_back)
        btn_layout.add_widget(add_ex_btn)
        btn_layout.add_widget(run_btn)
        btn_layout.add_widget(back_btn)
        self.root_layout.add_widget(btn_layout)

    def refresh_exercise_list(self, data):
        self.exercise_box.clear_widgets()
        if not data["exercises"]:
            self.exercise_box.add_widget(FLabel(text=self.tr("no_exercise"), size_hint_y=None, height=30))
        else:
            for i, ex in enumerate(data["exercises"]):
                txt = f"{ex['name']} - {ex['sets']} {self.tr('sets_short')} x {ex['reps']} {self.tr('reps_short')} | {self.tr('rest_short')} {ex['rest']}{self.tr('sec_short')}"
                ex_layout = BoxLayout(size_hint_y=None, height=30)
                ex_label = FLabel(text=txt)
                edit_btn = FButton(text=self.tr("edit"), size_hint_x=None, width=50)
                del_btn = FButton(text=self.tr("delete_short"), size_hint_x=None, width=50)
                edit_btn.bind(on_release=lambda x, idx=i: self.show_edit_exercise_popup(idx))
                del_btn.bind(on_release=lambda x, idx=i: self.delete_exercise(idx))
                ex_layout.add_widget(ex_label)
                ex_layout.add_widget(edit_btn)
                ex_layout.add_widget(del_btn)
                self.exercise_box.add_widget(ex_layout)

    # -------------------- EDIT EXERCISE --------------------
    def show_edit_exercise_popup(self, index):
        ex = self.routines[self.current_routine]["exercises"][index]
        layout = GridLayout(cols=2, spacing=10, padding=10, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))

        layout.add_widget(FLabel(text=self.tr("label_ex_name")))
        name_input = FTextInput(text=ex['name'], size_hint_y=None, height=40)
        layout.add_widget(name_input)

        layout.add_widget(FLabel(text=self.tr("label_sets")))
        sets_input = FTextInput(text=str(ex['sets']), input_filter="int", size_hint_y=None, height=40)
        layout.add_widget(sets_input)

        layout.add_widget(FLabel(text=self.tr("label_reps")))
        reps_input = FTextInput(text=str(ex['reps']), input_filter="int", size_hint_y=None, height=40)
        layout.add_widget(reps_input)

        layout.add_widget(FLabel(text=self.tr("label_rest_sec")))
        rest_input = FTextInput(text=str(ex['rest']), input_filter="int", size_hint_y=None, height=40)
        layout.add_widget(rest_input)

        btn_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        ok_btn = FButton(text=self.tr("yes"))
        cancel_btn = FButton(text=self.tr("no"))
        btn_layout.add_widget(ok_btn)
        btn_layout.add_widget(cancel_btn)

        outer = BoxLayout(orientation='vertical', spacing=10, padding=10)
        outer.add_widget(layout)
        outer.add_widget(btn_layout)

        popup = Popup(title=self.tr("edit_exercise"), content=outer, size_hint=(0.7, 0.7), auto_dismiss=False, title_font="NotoSansKR-VariableFont_wght.ttf")

        def save_changes(instance):
            ex['name'] = name_input.text.strip()
            ex['sets'] = int(sets_input.text.strip())
            ex['reps'] = int(reps_input.text.strip())
            ex['rest'] = int(rest_input.text.strip())
            self.save_data()
            popup.dismiss()
            self.refresh_exercise_list(self.routines[self.current_routine])

        ok_btn.bind(on_release=save_changes)
        cancel_btn.bind(on_release=popup.dismiss)
        popup.open()

    def delete_exercise(self, index):
        data = self.routines[self.current_routine]["exercises"]
        if 0 <= index < len(data):
            data.pop(index)
            self.save_data()
            self.refresh_exercise_list(self.routines[self.current_routine])

    # -------------------- ADD EXERCISE --------------------
    def show_add_exercise_popup(self, instance):
        layout = GridLayout(cols=2, spacing=10, padding=10, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))

        layout.add_widget(FLabel(text=self.tr("label_ex_name")))
        name_input = FTextInput(size_hint_y=None, height=40)
        layout.add_widget(name_input)

        layout.add_widget(FLabel(text=self.tr("label_sets")))
        sets_input = FTextInput(input_filter="int", size_hint_y=None, height=40)
        layout.add_widget(sets_input)

        layout.add_widget(FLabel(text=self.tr("label_reps")))
        reps_input = FTextInput(input_filter="int", size_hint_y=None, height=40)
        layout.add_widget(reps_input)

        layout.add_widget(FLabel(text=self.tr("label_rest_sec")))
        rest_input = FTextInput(input_filter="int", size_hint_y=None, height=40)
        layout.add_widget(rest_input)

        btn_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        ok_btn = FButton(text=self.tr("yes"))
        cancel_btn = FButton(text=self.tr("no"))
        btn_layout.add_widget(ok_btn)
        btn_layout.add_widget(cancel_btn)

        outer = BoxLayout(orientation='vertical', spacing=10, padding=10)
        outer.add_widget(layout)
        outer.add_widget(btn_layout)

        popup = Popup(title=self.tr("add_exercise"), content=outer, size_hint=(0.7, 0.7), auto_dismiss=False, title_font="NotoSansKR-VariableFont_wght.ttf")

        ok_btn.bind(on_release=lambda x: self.add_exercise(name_input.text, sets_input.text, reps_input.text, rest_input.text, popup))
        cancel_btn.bind(on_release=popup.dismiss)
        popup.open()

    def add_exercise(self, name, sets, reps, rest, popup):
        if not name.strip() or not sets.strip() or not reps.strip() or not rest.strip():
            return
        data = self.routines[self.current_routine]
        data["exercises"].append({
            "name": name,
            "sets": int(sets),
            "reps": int(reps),
            "rest": int(rest)
        })
        self.save_data()
        popup.dismiss()
        self.refresh_exercise_list(data)

    def go_back(self, instance=None):
        self.root_layout.clear_widgets()
        self.root_layout.add_widget(self.title_label)
        self.root_layout.add_widget(self.scroll)
        self.refresh_routine_list()

        add_btn = FButton(text=self.tr("add_routine"), size_hint_y=None, height=50, on_release=self.show_add_routine_popup)
        rec_btn = FButton(text=self.tr("records"), size_hint_y=None, height=50, on_release=self.show_records)
        lang_btn = FButton(text=self.lang.upper(), size_hint_y=None, height=50, on_release=self.show_language_toggle)
        self.root_layout.add_widget(add_btn)
        self.root_layout.add_widget(rec_btn)
        self.root_layout.add_widget(lang_btn)

    # -------------------- RUN ROUTINE --------------------
    def show_routine_type_popup(self, instance):
        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        seq_btn = FButton(text=self.tr("seq_mode"))
        circ_btn = FButton(text=self.tr("circuit_mode"))
        layout.add_widget(seq_btn)
        layout.add_widget(circ_btn)
        popup = Popup(title=self.tr("select_run_type"), content=layout, size_hint=(0.5, 0.4), auto_dismiss=True, title_font="NotoSansKR-VariableFont_wght.ttf")
        seq_btn.bind(on_release=lambda x: (popup.dismiss(), self.start_routine("sequential")))
        circ_btn.bind(on_release=lambda x: (popup.dismiss(), self.start_routine("circuit")))
        popup.open()

    def start_routine(self, r_type):
        self.routine_type = r_type
        self.data = self.routines[self.current_routine]["exercises"]
        if not self.data:
            return
        self.root_layout.clear_widgets()
        self.current_ex_index = 0
        self.current_set_per_ex = [0]*len(self.data)
        self.set_reps_accum = [0]*len(self.data)
        if self.routine_type == "sequential":
            self.ex_order = list(range(len(self.data)))
        else:  # circuit
            max_sets = max(ex["sets"] for ex in self.data)
            self.ex_order = []
            for s in range(max_sets):
                for i, ex in enumerate(self.data):
                    if self.current_set_per_ex[i] < ex["sets"]:
                        self.ex_order.append(i)
        self.show_exercise(self.ex_order[0])

    def show_exercise(self, ex_idx):
        self.root_layout.clear_widgets()
        idx = ex_idx
        self.current_ex_index = idx
        ex = self.data[idx]
        self.current_exercise = ex
        self.current_set = self.current_set_per_ex[idx] + 1
        self.exercise_label = FLabel(text=f"{ex['name']} ({self.tr('set_label')} {self.current_set}/{ex['sets']})", font_size=26, size_hint_y=None, height=50)
        self.root_layout.add_widget(self.exercise_label)
        self.actual_reps = 0
        self.rep_label = FLabel(text=f"{self.actual_reps}/{ex['reps']} {self.tr('reps_unit')}", font_size=22)
        self.root_layout.add_widget(self.rep_label)
        btn_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        plus_btn = FButton(text="+")
        minus_btn = FButton(text="-")
        done_btn = FButton(text=self.tr("complete"))
        btn_layout.add_widget(plus_btn)
        btn_layout.add_widget(minus_btn)
        btn_layout.add_widget(done_btn)
        self.root_layout.add_widget(btn_layout)
        plus_btn.bind(on_release=lambda x: self.add_rep())
        minus_btn.bind(on_release=lambda x: self.sub_rep())
        done_btn.bind(on_release=lambda x: self.complete_set())

    def add_rep(self):
        self.actual_reps += 1
        self.rep_label.text = f"{self.actual_reps}/{self.current_exercise['reps']} {self.tr('reps_unit')}"

    def sub_rep(self):
        if self.actual_reps > 0:
            self.actual_reps -= 1
            self.rep_label.text = f"{self.actual_reps}/{self.current_exercise['reps']} {self.tr('reps_unit')}"

    def start_rest(self, seconds):
        self.root_layout.clear_widgets()
        self.rest_time = seconds
        self.rest_label = FLabel(text=f"{self.tr('rest_label')}: {self.rest_time}{self.tr('sec_short')}", font_size=30)
        self.root_layout.add_widget(self.rest_label)

        Clock.schedule_interval(self.update_rest, 1)

    def update_rest(self, dt):
        self.rest_time -= 1
        if self.rest_time <= 0:
            Clock.unschedule(self.update_rest)
            self.show_exercise(self.current_ex_index)
        else:
            self.rest_label.text = f"{self.tr('rest_label')}: {self.rest_time}{self.tr('sec_short')}"

    def complete_set(self):
        idx = self.current_ex_index
        self.set_reps_accum[idx] += self.actual_reps
        self.current_set_per_ex[idx] += 1
        self.actual_reps = 0

        # Circuit
        if self.routine_type == "circuit":
            next_idx = None
            for i in range(idx + 1, len(self.ex_order)):
                if self.current_set_per_ex[self.ex_order[i]] < self.data[self.ex_order[i]]["sets"]:
                    next_idx = i
                    break
            if next_idx is not None:
                self.start_rest(self.data[idx]['rest'])  # 휴식 시작
            else:
                self.record_circuit_results()
                self.show_finish_screen()
        else:  # Sequential
            ex = self.current_exercise
            if self.current_set_per_ex[idx] < ex["sets"]:
                self.start_rest(ex['rest'])  # 휴식 시작
            else:
                next_idx = idx + 1
                if next_idx < len(self.data):
                    self.start_rest(self.data[idx]['rest'])  # 다음 운동 전 휴식
                else:
                    self.record_sequential_results()
                    self.show_finish_screen()

    # -------------------- RECORDING --------------------
    def record_sequential_results(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        record = {"date": now, "routine": self.current_routine}
        for i, ex in enumerate(self.data):
            record[ex['name']] = self.set_reps_accum[i]
        self.records.append(record)
        self.save_records()

    def record_circuit_results(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        record = {"date": now, "routine": self.current_routine}
        for i, ex in enumerate(self.data):
            record[ex['name']] = self.set_reps_accum[i]
        self.records.append(record)
        self.save_records()

    def show_records(self, instance=None):
        self.root_layout.clear_widgets()
        layout = BoxLayout(orientation='vertical', spacing=5)
        scroll = ScrollView()
        rec_box = BoxLayout(orientation='vertical', spacing=5, size_hint_y=None)
        rec_box.bind(minimum_height=rec_box.setter('height'))
        for i, rec in enumerate(self.records):
            ex_text = ", ".join(f"{k}:{v}" for k, v in rec.items() if k not in ["date", "routine"])
            text = f"{rec['date']} - {rec['routine']} - {ex_text}"
            rec_layout = BoxLayout(size_hint_y=None, height=30)
            lbl = FLabel(text=text)
            del_btn = FButton(text=self.tr("delete_short"), size_hint_x=None, width=50)
            del_btn.bind(on_release=lambda x, idx=i: self.delete_record(idx))
            rec_layout.add_widget(lbl)
            rec_layout.add_widget(del_btn)
            rec_box.add_widget(rec_layout)
        scroll.add_widget(rec_box)
        layout.add_widget(scroll)
        back_btn = FButton(text=self.tr("back"), size_hint_y=None, height=50, on_release=self.go_back)
        layout.add_widget(back_btn)
        self.root_layout.add_widget(layout)

    def delete_record(self, index):
        if 0 <= index < len(self.records):
            self.records.pop(index)
            self.save_records()
            self.show_records()

    # -------------------- FINISH --------------------
    def show_finish_screen(self):
        self.root_layout.clear_widgets()
        self.root_layout.add_widget(FLabel(text=self.tr("finish_msg"), font_size=30))
        back_btn = FButton(text=self.tr("back_to_routine"), size_hint_y=None, height=50, on_release=lambda x: self.open_routine(self.current_routine))
        self.root_layout.add_widget(back_btn)

    # -------------------- SAVE / LOAD --------------------
    def save_data(self):
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.routines, f, ensure_ascii=False, indent=4)

    def load_data(self):
        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_records(self):
        with open(RECORD_FILE, "w", encoding="utf-8") as f:
            json.dump(self.records, f, ensure_ascii=False, indent=4)

    def load_records(self):
        if os.path.exists(RECORD_FILE):
            with open(RECORD_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return []
if __name__ == "__main__":
    WorkoutApp().run()

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.menu import MDDropdownMenu
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
import subprocess
import os
import threading
import re
import queue

class MirrorApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "DeepOrange"
        self.theme_cls.accent_palette = "Gray"

        screen = MDScreen()
        layout = MDBoxLayout(orientation="vertical", padding=20, spacing=10)

        # Sekce zrcadlení
        mirror_label = MDLabel(
            text="Zrcadlení webu",
            halign="center",
            theme_text_color="Primary",
            size_hint=(1, None),
            height="30dp"
        )
        mirror_separator = MDBoxLayout(size_hint=(1, None), height="10dp", md_bg_color=[0.5, 0.5, 0.5, 0.2])

        self.url_input = MDTextField(
            hint_text="Zadej URL webu",
            helper_text="Např. https://example.com",
            mode="rectangle",
            icon_right="web",
            size_hint=(1, None),
            height="50dp"
        )

        self.depth_input = MDTextField(
            hint_text="Maximální hloubka (1-1000)",
            helper_text="Počet úrovní odkazů",
            mode="rectangle",
            input_filter="int",
            text="1000",
            size_hint=(1, None),
            height="50dp"
        )

        mirror_button_layout = MDBoxLayout(orientation="horizontal", spacing=10, padding=[0, 10, 0, 0])
        self.start_button = MDRaisedButton(
            text="Spustit zrcadlení",
            pos_hint={"center_x": 0.5},
            on_release=self.start_mirroring
        )
        self.stop_button = MDRaisedButton(
            text="Zastavit",
            pos_hint={"center_x": 0.5},
            disabled=True,
            on_release=self.stop_mirroring
        )
        mirror_button_layout.add_widget(self.start_button)
        mirror_button_layout.add_widget(self.stop_button)

        # Sekce nahrazování
        replace_label = MDLabel(
            text="Nahrazování textu",
            halign="center",
            theme_text_color="Primary",
            size_hint=(1, None),
            height="30dp"
        )
        replace_separator = MDBoxLayout(size_hint=(1, None), height="10dp", md_bg_color=[0.5, 0.5, 0.5, 0.2])

        self.replacements_input = MDTextField(
            hint_text="Cesta k souboru replacements.txt",
            helper_text="Např. ./replacements.txt s obsahem tohle_najdi|||nahrad_timto",
            mode="rectangle",
            icon_right="file-document",
            text="replacements.txt",
            size_hint=(1, None),
            height="50dp"
        )

        self.folder_input = MDTextField(
            hint_text="Vybraná složka z mirror_output",
            helper_text="Klikni na tlačítko pro výběr",
            mode="rectangle",
            text="mirror_output",
            size_hint=(0.8, None),
            height="50dp",
            disabled=True
        )
        self.folder_button = MDRaisedButton(
            text="Vybrat",
            size_hint=(0.2, None),
            height="50dp",
            on_release=self.open_folder_menu
        )
        folder_layout = MDBoxLayout(orientation="horizontal", spacing=10)
        folder_layout.add_widget(self.folder_input)
        folder_layout.add_widget(self.folder_button)

        self.replace_button = MDRaisedButton(
            text="Nahradit text",
            pos_hint={"center_x": 0.5},
            on_release=self.replace_text
        )

        # Společné prvky
        self.progress = MDProgressBar(
            value=0,
            size_hint=(1, None),
            height="20dp"
        )

        self.log = MDLabel(
            text="Připraveno",
            halign="left",
            valign="top",
            size_hint=(1, 1),
            text_size=(None, None)
        )
        scroll = ScrollView()
        scroll.add_widget(self.log)

        layout.add_widget(mirror_label)
        layout.add_widget(mirror_separator)
        layout.add_widget(self.url_input)
        layout.add_widget(self.depth_input)
        layout.add_widget(mirror_button_layout)
        layout.add_widget(replace_label)
        layout.add_widget(replace_separator)
        layout.add_widget(self.replacements_input)
        layout.add_widget(folder_layout)
        layout.add_widget(self.replace_button)
        layout.add_widget(self.progress)
        layout.add_widget(scroll)
        screen.add_widget(layout)

        self.running = False
        self.output_dir = "mirror_output"
        self.selected_folder = self.output_dir
        self.log_queue = queue.Queue()
        self.downloaded_files = 0
        self.total_files = 0  # Odhad celkového počtu souborů

        return screen

    def update_log(self, message):
        self.log.text += f"\n{message}"
        self.root.children[0].children[1].scroll_y = 0

    def open_folder_menu(self, instance):
        if not os.path.exists(self.output_dir):
            self.show_error("Nejprve proveď zrcadlení, aby byly k dispozici složky!")
            return

        folders = [self.output_dir] + [os.path.join(self.output_dir, d) for d in os.listdir(self.output_dir) if os.path.isdir(os.path.join(self.output_dir, d))]
        menu_items = [{"text": os.path.basename(f) or "root", "viewclass": "OneLineListItem", "on_release": lambda x=f: self.set_folder(x)} for f in folders]
        self.folder_menu = MDDropdownMenu(caller=instance, items=menu_items, width_mult=4)
        self.folder_menu.open()

    def set_folder(self, folder_path):
        self.selected_folder = folder_path
        self.folder_input.text = os.path.basename(folder_path) or "root"
        self.folder_menu.dismiss()

    def start_mirroring(self, instance):
        url = self.url_input.text.strip()
        depth = int(self.depth_input.text or 1)

        if not url.startswith("http"):
            self.show_error("Zadej platnou URL začínající na http/https!")
            return

        self.running = True
        self.start_button.disabled = True
        self.stop_button.disabled = False
        self.replace_button.disabled = True
        self.progress.value = 0
        self.downloaded_files = 0
        self.total_files = 0
        self.update_log(f"Spouštím zrcadlení: {url}")

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        threading.Thread(target=self.mirror_site, args=(url, depth)).start()
        Clock.schedule_interval(self.update_progress, 0.5)
        Clock.schedule_interval(self.process_log_queue, 0.1)

    def stop_mirroring(self, instance):
        self.running = False
        if hasattr(self, "process") and self.process:
            self.process.terminate()
        self.start_button.disabled = False
        self.stop_button.disabled = True
        self.replace_button.disabled = False
        self.update_log("Zrcadlení zastaveno uživatelem.")
        Clock.unschedule(self.process_log_queue)

    def mirror_site(self, url, max_depth):
        try:
            cmd = [
                "wget2",
                "--progress=bar",
                "--mirror",
                f"--level={max_depth}",
                "--convert-links",
                "--adjust-extension",
                "--page-requisites",
                f"--directory-prefix={self.output_dir}",
                url
            ]
            self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, universal_newlines=True)
            
            while self.running and self.process.poll() is None:
                stdout_line = self.process.stdout.readline()
                stderr_line = self.process.stderr.readline()
                if stdout_line:
                    self.log_queue.put(f"[wget2] {stdout_line.strip()}")
                    if "%[" in stdout_line:  # Detekce progress baru
                        self.downloaded_files += 1
                        if "Files:" in stdout_line and "Todo:" in stdout_line:
                            files_match = re.search(r"Files: (\d+)", stdout_line)
                            todo_match = re.search(r"Todo: (\d+)", stdout_line)
                            if files_match and todo_match:
                                self.total_files = int(files_match.group(1)) + int(todo_match.group(1))
                if stderr_line:
                    self.log_queue.put(f"[wget2 ERROR] {stderr_line.strip()}")

            stdout, stderr = self.process.communicate()
            if stdout:
                for line in stdout.splitlines():
                    self.log_queue.put(f"[wget2] {line.strip()}")
            if stderr:
                for line in stderr.splitlines():
                    self.log_queue.put(f"[wget2 ERROR] {line.strip()}")

            if self.running:
                if self.process.returncode == 0:
                    self.update_log("Zrcadlení dokončeno!")
                else:
                    self.update_log(f"Chyba při zrcadlení, kód: {self.process.returncode}")
            self.running = False
            self.start_button.disabled = False
            self.stop_button.disabled = True
            self.replace_button.disabled = False

        except FileNotFoundError:
            self.update_log("Chyba: wget2 není nainstalován na tvém systému!")
            self.running = False
            self.start_button.disabled = False
            self.stop_button.disabled = True
            self.replace_button.disabled = False
        except Exception as e:
            self.update_log(f"Chyba: {str(e)}")
            self.running = False
            self.start_button.disabled = False
            self.stop_button.disabled = True
            self.replace_button.disabled = False

    def process_log_queue(self, dt):
        while not self.log_queue.empty():
            message = self.log_queue.get()
            self.update_log(message)

    def update_progress(self, dt):
        if self.running and self.total_files > 0:
            progress = min((self.downloaded_files / self.total_files) * 100, 90)  # Max 90%, dokud neskončí
            self.progress.value = progress
        elif not self.running:
            self.progress.value = 100
            Clock.unschedule(self.update_progress)

    def replace_text(self, instance):
        replacements_file = self.replacements_input.text.strip()
        target_folder = self.selected_folder

        if not os.path.exists(replacements_file):
            self.show_error(f"Soubor {replacements_file} nebyl nalezen!")
            return

        if not os.path.exists(target_folder):
            self.show_error(f"Složka {target_folder} nebyla nalezena!")
            return

        replacements = {}
        try:
            with open(replacements_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and "|||" in line:
                        search_text, replace_text = line.split("|||", 1)
                        replacements[search_text] = replace_text
            if not replacements:
                self.show_error("Soubor je prázdný nebo neobsahuje platná pravidla ve formátu 'hledaný_text|||nahrazující_text'!")
                return
        except Exception as e:
            self.show_error(f"Chyba při čtení souboru: {str(e)}")
            return

        self.update_log(f"Spouštím nahrazování textů ve složce: {target_folder}")
        total_replaced = 0

        for root, _, files in os.walk(target_folder):
            for file in files:
                if file.endswith((".html", ".htm", ".css", ".js")):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        original_content = content
                        for search_text, replace_text in replacements.items():
                            content, count = re.subn(re.escape(search_text), replace_text, content)
                            total_replaced += count
                        if content != original_content:
                            with open(file_path, "w", encoding="utf-8") as f:
                                f.write(content)
                            self.update_log(f"Upraven soubor: {file_path}")
                    except Exception as e:
                        self.update_log(f"Chyba při zpracování {file_path}: {str(e)}")

        self.update_log(f"Celkem nahrazeno: {total_replaced} výskytů.")

    def show_error(self, message):
        dialog = MDDialog(
            title="Chyba",
            text=message,
            buttons=[MDFlatButton(text="OK", on_release=lambda x: dialog.dismiss())]
        )
        dialog.open()

if __name__ == "__main__":
    MirrorApp().run()

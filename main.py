from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from plyer import filechooser
import subprocess
import os
import threading
import re

class MirrorApp(MDApp):
    def build(self):
        # Nastavení vzhledu
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "DeepOrange"
        self.theme_cls.accent_palette = "Gray"

        # Hlavní obrazovka
        screen = MDScreen()
        layout = MDBoxLayout(orientation="vertical", padding=20, spacing=20)

        # Vstupní pole pro URL
        self.url_input = MDTextField(
            hint_text="Zadej URL webu",
            helper_text="Např. https://example.com",
            mode="rectangle",
            icon_right="web",
            size_hint=(1, None),
            height="50dp"
        )

        # Nastavení hloubky prohledávání
        self.depth_input = MDTextField(
            hint_text="Maximální hloubka (1-5)",
            helper_text="Počet úrovní odkazů",
            mode="rectangle",
            input_filter="int",
            text="1",
            size_hint=(1, None),
            height="50dp"
        )

        # Vstupní pole pro cestu k replacements.txt
        self.replacements_input = MDTextField(
            hint_text="Cesta k souboru replacements.txt",
            helper_text="Např. ./replacements.txt",
            mode="rectangle",
            icon_right="file-document",
            text="replacements.txt",
            size_hint=(1, None),
            height="50dp"
        )

        # Vstupní pole pro složku k nahrazování
        self.folder_input = MDTextField(
            hint_text="Cesta ke složce pro nahrazování",
            helper_text="Vyber složku tlačítkem vpravo",
            mode="rectangle",
            icon_right="folder",
            text="mirror_output",
            size_hint=(0.8, None),
            height="50dp"
        )
        folder_button = MDRaisedButton(
            text="Vybrat",
            size_hint=(0.2, None),
            height="50dp",
            on_release=self.select_folder
        )
        folder_layout = MDBoxLayout(orientation="horizontal", spacing=10)
        folder_layout.add_widget(self.folder_input)
        folder_layout.add_widget(folder_button)

        # Progress bar
        self.progress = MDProgressBar(
            value=0,
            size_hint=(1, None),
            height="20dp"
        )

        # Logovací okno
        self.log = MDLabel(
            text="Připraveno",
            halign="left",
            valign="top",
            size_hint=(1, 1),
            text_size=(None, None)
        )
        scroll = ScrollView()
        scroll.add_widget(self.log)

        # Tlačítka
        button_layout = MDBoxLayout(orientation="horizontal", spacing=10, padding=[0, 10, 0, 0])
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
        self.replace_button = MDRaisedButton(
            text="Nahradit text",
            pos_hint={"center_x": 0.5},
            on_release=self.replace_text
        )
        button_layout.add_widget(self.start_button)
        button_layout.add_widget(self.stop_button)
        button_layout.add_widget(self.replace_button)

        # Sestavení rozložení
        layout.add_widget(self.url_input)
        layout.add_widget(self.depth_input)
        layout.add_widget(self.replacements_input)
        layout.add_widget(folder_layout)
        layout.add_widget(self.progress)
        layout.add_widget(scroll)
        layout.add_widget(button_layout)
        screen.add_widget(layout)

        # Proměnné pro řízení
        self.running = False
        self.process = None
        self.output_dir = "mirror_output"

        return screen

    def update_log(self, message):
        """Aktualizuje logovací okno."""
        self.log.text += f"\n{message}"
        self.root.children[0].children[1].scroll_y = 0

    def select_folder(self, instance):
        """Otevře dialog pro výběr složky."""
        path = filechooser.choose_dir(title="Vyber složku pro nahrazování")
        if path:
            self.folder_input.text = path[0]

    def start_mirroring(self, instance):
        """Spustí zrcadlení webu pomocí wget2."""
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
        self.update_log(f"Spouštím zrcadlení: {url}")

        # Vytvoření výstupní složky
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        # Spuštění wget2 v samostatném vlákně
        threading.Thread(target=self.mirror_site, args=(url, depth)).start()
        Clock.schedule_interval(self.update_progress, 0.5)

    def stop_mirroring(self, instance):
        """Zastaví proces zrcadlení."""
        if self.process:
            self.process.terminate()
        self.running = False
        self.start_button.disabled = False
        self.stop_button.disabled = True
        self.replace_button.disabled = False
        self.update_log("Zrcadlení zastaveno uživatelem.")

    def mirror_site(self, url, max_depth):
        """Spustí wget2 pro zrcadlení webu."""
        try:
            cmd = [
                "wget2",
                "-k",
                f"--level={max_depth}",
                "-E",
                "-r",
                "-p",
                "-N",
                "-F",
                "--cut-file-get-vars",
                "--restrict-file-names=windows",
                "-nH",
                f"--directory-prefix={self.output_dir}",
                url
            ]
            self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = self.process.communicate()

            if self.running:
                if self.process.returncode == 0:
                    self.update_log("Zrcadlení dokončeno!")
                else:
                    self.update_log(f"Chyba při zrcadlení: {stderr}")
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

    def replace_text(self, instance):
        """Vyhledá a nahradí text ve stažených souborech podle replacements.txt."""
        replacements_file = self.replacements_input.text.strip()
        target_folder = self.folder_input.text.strip()

        if not os.path.exists(replacements_file):
            self.show_error(f"Soubor {replacements_file} nebyl nalezen!")
            return

        if not os.path.exists(target_folder):
            self.show_error(f"Složka {target_folder} nebyla nalezena!")
            return

        # Načtení nahrazovacích pravidel s oddělovačem |||
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
                if file.endswith((".html", ".htm", ".css", ".js")):  # Pouze textové soubory
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

    def update_progress(self, dt):
        """Simuluje progress (wget2 neposkytuje přímý průběh)."""
        if self.running:
            if self.progress.value < 90:  # Necháme 100% až na konec
                self.progress.value += 5
        else:
            self.progress.value = 100
            Clock.unschedule(self.update_progress)

    def show_error(self, message):
        """Zobrazí chybové dialogové okno."""
        dialog = MDDialog(
            title="Chyba",
            text=message,
            buttons=[MDFlatButton(text="OK", on_release=lambda x: dialog.dismiss())]
        )
        dialog.open()

if __name__ == "__main__":
    MirrorApp().run()

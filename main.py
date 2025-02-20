import os
import shutil
import threading
import subprocess
import re
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.progressbar import ProgressBar
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.popup import Popup

def has_write_permissions(folder):
    test_file = os.path.join(folder, "test_write.tmp")
    try:
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        return True
    except:
        return False

class StaticSiteMirrorApp(App):
    def build(self):
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        self.url_input = TextInput(hint_text='Zadej URL', size_hint=(1, 0.1))
        self.layout.add_widget(self.url_input)
        
        self.select_folder_button = Button(text='Vyber složku', size_hint=(1, 0.1))
        self.select_folder_button.bind(on_press=self.open_file_chooser)
        self.layout.add_widget(self.select_folder_button)
        
        self.replacements_input = TextInput(hint_text='Nahrazení (co > čím, jeden řádek = jedna náhrada)', size_hint=(1, 0.2), multiline=True)
        self.replacements_input.text = "asset/ > /static/\n.html > /"
        self.layout.add_widget(self.replacements_input)
        
        self.download_button = Button(text='Stáhnout statický otisk', size_hint=(1, 0.1))
        self.download_button.bind(on_press=self.start_download)
        self.layout.add_widget(self.download_button)
        
        self.modify_button = Button(text='Oddebilnit na Vexe.cz', size_hint=(1, 0.1))
        self.modify_button.bind(on_press=self.start_modification)
        self.layout.add_widget(self.modify_button)
        
        self.progress = ProgressBar(max=100, value=0, size_hint=(1, 0.1))
        self.layout.add_widget(self.progress)
        
        self.status_label = Label(text='Status: Čekám na akci...', size_hint=(1, 0.1))
        self.layout.add_widget(self.status_label)
        
        self.selected_folder = ''
        return self.layout


    def start_download(self, instance):
        if not self.url_input.text or not self.selected_folder:
            self.status_label.text = 'Zadej URL a vyber složku!'
            return
        
        threading.Thread(target=self.download_site).start()
    
    def download_site(self):
        url = self.url_input.text
        domain = url.split('//')[-1].split('/')[0]
        save_path = os.path.join(self.selected_folder, domain)
        
        if os.path.exists(save_path):
            shutil.rmtree(save_path)
        os.makedirs(save_path, exist_ok=True)
        
        self.status_label.text = 'Stahuji stránku...'
        
        wget_path = os.path.join(os.path.dirname(__file__), 'bin', 'wget2.exe')
        if not os.path.exists(wget_path):
            wget_path = 'wget2'
        
        command = f"{wget_path} -k -K -E -r -l 10 -p -N -F --cut-file-get-vars --restrict-file-names=windows -nH {url}"
        
        process = subprocess.Popen(command, shell=True, cwd=save_path, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        for line in process.stdout:
            if '%' in line:
                try:
                    progress = int(re.search(r'(\d+)%', line).group(1))
                    self.progress.value = progress
                except:
                    pass
        
        process.wait()
        self.status_label.text = 'Stažení dokončeno!'
        self.progress.value = 50
    
    def open_file_chooser(self, instance):
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        file_chooser = FileChooserListView(size_hint=(1, 0.8), dirselect=True)
        confirm_button = Button(text='Potvrdit složku', size_hint=(1, 0.2))
        
        def confirm_selection(instance):
            if file_chooser.selection:
                selected = file_chooser.selection[0]
                if not has_write_permissions(selected):
                    self.status_label.text = 'Chyba: Nemáš práva pro zápis do této složky!'
                else:
                    self.selected_folder = selected
                    self.status_label.text = f'Vybraná složka: {self.selected_folder}'
                    self.select_folder_button.text = f'Složka: {os.path.basename(self.selected_folder)}'
                    popup.dismiss()
        
        confirm_button.bind(on_press=confirm_selection)
        content.add_widget(file_chooser)
        content.add_widget(confirm_button)
        
        popup = Popup(title='Vyber složku', content=content, size_hint=(0.9, 0.9))
        popup.open()

    def start_modification(self, instance):
        if not self.selected_folder:
            self.status_label.text = 'Vyber složku ke zpracování!'
            return
        
        threading.Thread(target=self.modify_html_files).start()
    
    def modify_html_files(self):
        self.status_label.text = 'Upravuji HTML soubory...'
        replacements = [line.split(' > ') for line in self.replacements_input.text.split('\n') if ' > ' in line]
        
        templates_dir = os.path.join(self.selected_folder, 'templates', 'page')
        public_dir = os.path.join(self.selected_folder, 'public')
        os.makedirs(templates_dir, exist_ok=True)
        os.makedirs(public_dir, exist_ok=True)
        
        for root, dirs, files in os.walk(self.selected_folder):
            dirs[:] = [d for d in dirs if d not in ['templates', 'public']]
            
            for file in files:
                file_path = os.path.join(root, file)
                
                if file.endswith('.html'):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    for old, new in replacements:
                        content = content.replace(old, new)
                    
                    content = re.sub(r'href="(?!http)(?!/)(.*?)"', r'href="/\1"', content)
                    
                    new_file_path = os.path.join(templates_dir, os.path.relpath(file_path, self.selected_folder))
                    os.makedirs(os.path.dirname(new_file_path), exist_ok=True)
                    shutil.move(file_path, new_file_path)
                    with open(new_file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                elif file.endswith('.orig'):
                    os.remove(file_path)
                else:
                    rel_path = os.path.relpath(file_path, self.selected_folder)
                    new_static_path = os.path.join(public_dir, rel_path)
                    os.makedirs(os.path.dirname(new_static_path), exist_ok=True)
                    shutil.move(file_path, new_static_path)
        
        self.status_label.text = 'Úprava dokončena!'
        self.progress.value = 100

if __name__ == '__main__':
    StaticSiteMirrorApp().run()

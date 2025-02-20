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

    def modify_html_files(self):
        self.status_label.text = 'Upravuji HTML soubory...'
        replacements = [line.split(' > ') for line in self.replacements_input.text.split('\n') if ' > ' in line]
        
        templates_dir = os.path.join(self.selected_folder, 'templates', 'page')
        public_dir = os.path.join(self.selected_folder, 'public')
        os.makedirs(templates_dir, exist_ok=True)
        os.makedirs(public_dir, exist_ok=True)
        
        for root, dirs, files in os.walk(self.selected_folder):
            # Vyloučení složek templates a public z kopírování
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
            
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                rel_path = os.path.relpath(dir_path, self.selected_folder)
                new_static_path = os.path.join(public_dir, rel_path)
                if not os.path.exists(new_static_path):
                    shutil.move(dir_path, new_static_path)
        
        self.status_label.text = 'Úprava dokončena!'
        self.progress.value = 100

if __name__ == '__main__':
    StaticSiteMirrorApp().run()

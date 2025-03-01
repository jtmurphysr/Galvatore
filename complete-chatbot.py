import sys
import os
import uuid
import configparser
import json
from datetime import datetime
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QTextEdit, 
                            QLineEdit, QPushButton, QHBoxLayout, QLabel, 
                            QScrollArea, QSizePolicy, QMessageBox, QFileDialog,
                            QMenu, QDialog, QListWidget, QInputDialog)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QFont, QAction
from openai import OpenAI
import requests
from playsound import playsound

class Config:
    """Configuration handler for API keys and settings"""
    def __init__(self):
        self.config_file = Path.home() / '.chatbot_config.ini'
        self.config = configparser.ConfigParser()
        
        # Default values
        self.openai_api_key = ""
        self.elevenlabs_api_key = ""
        self.elevenlabs_voice_id = ""
        self.tts_enabled = True
        self.model = "gpt-4"
        self.context_dir = Path('chat_contexts')
        self.assistant_name = "AI"
        
        # Set path for the ai_guidance.ini file
        self.guidance_file = Path('ai_guidance.ini')
        
        # Create ai_guidance.ini file if it doesn't exist
        if not self.guidance_file.exists():
            try:
                guidance_config = configparser.ConfigParser()
                guidance_config['AI_GUIDANCE'] = {
                    'system_prompt': "You are a helpful assistant. Please respond in a conversational tone, providing thoughtful and detailed answers. Feel free to ask clarifying questions when needed."
                }
                
                with open(self.guidance_file, 'w', encoding='utf-8') as f:
                    guidance_config.write(f)
            except Exception as e:
                print(f"Error creating ai_guidance.ini file: {e}")
        
        # Create contexts directory if it doesn't exist
        self.context_dir.mkdir(exist_ok=True)
        
        self.load_config()
    
    def load_config(self):
        """Load configuration from file or create default if doesn't exist"""
        if self.config_file.exists():
            self.config.read(self.config_file)
            self.openai_api_key = self.config.get('API', 'openai_api_key', fallback="")
            self.elevenlabs_api_key = self.config.get('API', 'elevenlabs_api_key', fallback="")
            self.elevenlabs_voice_id = self.config.get('API', 'elevenlabs_voice_id', fallback="")
            self.tts_enabled = self.config.getboolean('Settings', 'tts_enabled', fallback=True)
            self.model = self.config.get('API', 'model', fallback="gpt-4")
            self.assistant_name = self.config.get('Settings', 'assistant_name', fallback="AI")
        else:
            self.create_default_config()
    
    def create_default_config(self):
        """Create a default configuration file"""
        self.config['API'] = {
            'openai_api_key': '',
            'elevenlabs_api_key': '',
            'elevenlabs_voice_id': '',
            'model': 'gpt-4'
        }
        self.config['Settings'] = {
            'tts_enabled': 'true',
            'assistant_name': 'AI'
        }
        
        # Create the directory if it doesn't exist
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.config_file, 'w') as f:
            self.config.write(f)
    
    def save_config(self):
        """Save current configuration to file"""
        self.config['API'] = {
            'openai_api_key': self.openai_api_key,
            'elevenlabs_api_key': self.elevenlabs_api_key,
            'elevenlabs_voice_id': self.elevenlabs_voice_id,
            'model': self.model
        }
        self.config['Settings'] = {
            'tts_enabled': str(self.tts_enabled).lower(),
            'assistant_name': self.assistant_name
        }
        
        with open(self.config_file, 'w') as f:
            self.config.write(f)


# ================== WORKER THREAD FOR OPENAI REQUEST ===================
class OpenAIWorker(QThread):
    response_signal = pyqtSignal(str)  # Signal to send response back to GUI
    error_signal = pyqtSignal(str)     # Signal to send errors back to GUI

    def __init__(self, prompt, api_key, chat_history=None, system_prompt=None):
        super().__init__()
        self.prompt = prompt
        self.api_key = api_key
        self.chat_history = chat_history or []
        self.system_prompt = system_prompt or "You are a helpful assistant."
        self.model = "gpt-4"  # Default model

    def run(self):
        try:
            # Check if API key is set
            if not self.api_key:
                self.error_signal.emit("Error: OpenAI API key is not set. Please set it in settings.")
                return
            
            # Create OpenAI client with API key
            client = OpenAI(api_key=self.api_key)
            
            # Get system prompt from ai_guidance.ini file in the current directory
            system_content = self.system_prompt
            system_prompt_file = Path('ai_guidance.ini')
            
            if system_prompt_file.exists():
                try:
                    guidance_config = configparser.ConfigParser()
                    guidance_config.read(system_prompt_file)
                    
                    if 'AI_GUIDANCE' in guidance_config and 'system_prompt' in guidance_config['AI_GUIDANCE']:
                        system_content = guidance_config['AI_GUIDANCE']['system_prompt']
                except Exception as e:
                    print(f"Error reading ai_guidance.ini file: {e}")
            
            # Prepare messages
            messages = [{"role": "system", "content": system_content}]
            
            # Add chat history if available
            for message in self.chat_history:
                if message["role"] in ["user", "assistant"]:
                    messages.append(message)
            
            # Add the current user message if not already in chat history
            if not self.chat_history or self.chat_history[-1]["content"] != self.prompt:
                messages.append({"role": "user", "content": self.prompt})
            
            # Get model from config if available
            if hasattr(self, 'config') and hasattr(self.config, 'model'):
                self.model = self.config.model
            
            # Make API request with new client-based approach
            response = client.chat.completions.create(
                model=self.model,
                messages=messages
            )
            ai_text = response.choices[0].message.content
            self.response_signal.emit(ai_text)
        except Exception as e:
            self.error_signal.emit(f"Error: {str(e)}")


# ================== WORKER THREAD FOR ELEVENLABS TTS ===================
class ElevenLabsWorker(QThread):
    error_signal = pyqtSignal(str)  # Signal to send errors back to GUI
    
    def __init__(self, text, api_key, voice_id):
        super().__init__()
        self.text = text
        self.api_key = api_key
        self.voice_id = voice_id

    def run(self):
        try:
            # Check if API key and voice ID are set
            if not self.api_key or not self.voice_id:
                self.error_signal.emit("Error: ElevenLabs API key or voice ID is not set. Text-to-speech is disabled.")
                return
                
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
            headers = {
                "xi-api-key": self.api_key,
                "Content-Type": "application/json"
            }
            data = {
                "text": self.text, 
                "voice_settings": {
                    "stability": 0.5, 
                    "similarity_boost": 0.8
                }
            }

            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                # Create a temp directory if it doesn't exist
                temp_dir = Path.home() / '.chatbot_temp'
                temp_dir.mkdir(parents=True, exist_ok=True)
                
                audio_file = temp_dir / f"output_{uuid.uuid4()}.mp3"
                with open(audio_file, "wb") as f:
                    f.write(response.content)
                playsound(str(audio_file))  # Play sound
                os.remove(audio_file)  # Cleanup
            else:
                error_msg = f"TTS Error: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f" - {error_data.get('detail', {}).get('message', '')}"
                except:
                    pass
                self.error_signal.emit(error_msg)
        except Exception as e:
            self.error_signal.emit(f"TTS Exception: {str(e)}")


# ================== LOAD CONVERSATION DIALOG ===================
class LoadConversationDialog(QDialog):
    def __init__(self, context_dir):
        super().__init__()
        self.context_dir = context_dir
        self.selected_file = None
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle("Load Conversation")
        self.setGeometry(200, 200, 400, 300)
        
        layout = QVBoxLayout()
        
        # List of saved conversations
        self.conversation_list = QListWidget()
        self.refresh_conversations()
        self.conversation_list.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.conversation_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        load_button = QPushButton("Load")
        load_button.clicked.connect(self.accept)
        button_layout.addWidget(load_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(self.delete_conversation)
        button_layout.addWidget(delete_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def refresh_conversations(self):
        """Refresh the list of conversations"""
        self.conversation_list.clear()
        
        # Get all JSON files in the context directory
        files = sorted(self.context_dir.glob('*.json'), key=os.path.getmtime, reverse=True)
        
        for file in files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Display the title and date
                    timestamp = datetime.fromtimestamp(os.path.getmtime(file))
                    item_text = f"{file.stem} - {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                    if 'title' in data and data['title']:
                        item_text = f"{data['title']} - {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                    self.conversation_list.addItem(item_text)
                    # Store the filename as item data
                    self.conversation_list.item(self.conversation_list.count()-1).setData(Qt.ItemDataRole.UserRole, str(file))
            except Exception as e:
                print(f"Error loading conversation file {file}: {e}")
    
    def get_selected_file(self):
        """Get the selected conversation file"""
        current_item = self.conversation_list.currentItem()
        if current_item:
            return current_item.data(Qt.ItemDataRole.UserRole)
        return None
    
    def delete_conversation(self):
        """Delete the selected conversation"""
        current_item = self.conversation_list.currentItem()
        if current_item:
            file_path = current_item.data(Qt.ItemDataRole.UserRole)
            
            # Confirm deletion
            reply = QMessageBox.question(
                self, 
                "Confirm Deletion",
                f"Are you sure you want to delete this conversation?\nThis cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    os.remove(file_path)
                    self.refresh_conversations()
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Failed to delete conversation: {str(e)}")
        else:
            QMessageBox.information(self, "Information", "Please select a conversation to delete.")


# ================== SETTINGS DIALOG ===================
class SettingsDialog(QWidget):
    settings_updated = pyqtSignal()
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle("Chatbot Settings")
        self.setGeometry(150, 150, 600, 400)
        
        layout = QVBoxLayout()
        
        # OpenAI API Key
        layout.addWidget(QLabel("OpenAI API Key:"))
        self.openai_key_input = QLineEdit()
        self.openai_key_input.setText(self.config.openai_api_key)
        self.openai_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.openai_key_input)
        
        # ElevenLabs API Key
        layout.addWidget(QLabel("ElevenLabs API Key:"))
        self.elevenlabs_key_input = QLineEdit()
        self.elevenlabs_key_input.setText(self.config.elevenlabs_api_key)
        self.elevenlabs_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.elevenlabs_key_input)
        
        # ElevenLabs Voice ID
        layout.addWidget(QLabel("ElevenLabs Voice ID:"))
        self.elevenlabs_voice_input = QLineEdit()
        self.elevenlabs_voice_input.setText(self.config.elevenlabs_voice_id)
        layout.addWidget(self.elevenlabs_voice_input)
        
        # Assistant Name
        layout.addWidget(QLabel("Assistant Name:"))
        self.assistant_name_input = QLineEdit()
        self.assistant_name_input.setText(self.config.assistant_name)
        self.assistant_name_input.setPlaceholderText("AI")
        layout.addWidget(self.assistant_name_input)
        
        # Model Selection
        layout.addWidget(QLabel("OpenAI Model:"))
        self.model_input = QLineEdit()
        self.model_input.setText(self.config.model)
        self.model_input.setPlaceholderText("gpt-4")
        layout.addWidget(self.model_input)
        
        # TTS Enabled Checkbox
        self.tts_checkbox = QPushButton("Enable Text-to-Speech")
        self.tts_checkbox.setCheckable(True)
        self.tts_checkbox.setChecked(self.config.tts_enabled)
        layout.addWidget(self.tts_checkbox)
        
        # System Prompt Editor
        layout.addWidget(QLabel("System Prompt (AI Personality & Instructions):"))
        self.system_prompt_edit = QTextEdit()
        try:
            guidance_config = configparser.ConfigParser()
            guidance_config.read(self.config.guidance_file)
            
            if 'AI_GUIDANCE' in guidance_config and 'system_prompt' in guidance_config['AI_GUIDANCE']:
                self.system_prompt_edit.setText(guidance_config['AI_GUIDANCE']['system_prompt'])
            else:
                self.system_prompt_edit.setText("Default system prompt not found in ai_guidance.ini")
        except Exception as e:
            self.system_prompt_edit.setText("Error loading ai_guidance.ini file.")
            print(f"Error loading ai_guidance.ini file: {e}")
        
        self.system_prompt_edit.setMinimumHeight(150)
        layout.addWidget(self.system_prompt_edit)
        
        # Save Button
        self.save_button = QPushButton("Save Settings")
        self.save_button.clicked.connect(self.save_settings)
        layout.addWidget(self.save_button)
        
        self.setLayout(layout)
    
    def save_settings(self):
        self.config.openai_api_key = self.openai_key_input.text()
        self.config.elevenlabs_api_key = self.elevenlabs_key_input.text()
        self.config.elevenlabs_voice_id = self.elevenlabs_voice_input.text()
        self.config.tts_enabled = self.tts_checkbox.isChecked()
        self.config.model = self.model_input.text() or "gpt-4"
        self.config.assistant_name = self.assistant_name_input.text() or "AI"
        
        # Save system prompt to ai_guidance.ini file
        try:
            guidance_config = configparser.ConfigParser()
            
            # Read existing file if it exists
            if self.config.guidance_file.exists():
                guidance_config.read(self.config.guidance_file)
            
            # Make sure the section exists
            if 'AI_GUIDANCE' not in guidance_config:
                guidance_config['AI_GUIDANCE'] = {}
            
            # Update the system prompt
            guidance_config['AI_GUIDANCE']['system_prompt'] = self.system_prompt_edit.toPlainText()
            
            # Write to file
            with open(self.config.guidance_file, 'w', encoding='utf-8') as f:
                guidance_config.write(f)
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Failed to save system prompt to ai_guidance.ini: {str(e)}")
        
        self.config.save_config()
        self.settings_updated.emit()
        QMessageBox.information(self, "Settings", "Settings saved successfully!")
        self.close()


# ================== PYQT6 CHATBOT UI ===================
class ChatbotApp(QWidget):
    def __init__(self):
        super().__init__()
        self.config = Config()
        self.chat_history = []
        self.system_prompt = ""
        self.current_conversation_file = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle("AI Chatbot with Speech")
        self.setGeometry(100, 100, 800, 600)

        main_layout = QVBoxLayout()

        # Create menu bar
        menu_layout = QHBoxLayout()
        
        # File Menu Button
        self.file_menu_button = QPushButton("File")
        self.file_menu = QMenu(self)
        
        self.new_action = QAction("New Conversation", self)
        self.new_action.triggered.connect(self.new_conversation)
        self.file_menu.addAction(self.new_action)
        
        self.save_action = QAction("Save Conversation", self)
        self.save_action.triggered.connect(self.save_conversation)
        self.file_menu.addAction(self.save_action)
        
        self.save_as_action = QAction("Save Conversation As...", self)
        self.save_as_action.triggered.connect(self.save_conversation_as)
        self.file_menu.addAction(self.save_as_action)
        
        self.load_action = QAction("Load Conversation", self)
        self.load_action.triggered.connect(self.load_conversation)
        self.file_menu.addAction(self.load_action)
        
        self.file_menu_button.setMenu(self.file_menu)
        menu_layout.addWidget(self.file_menu_button)
        
        # Add a spacer
        menu_layout.addStretch()
        
        # Current conversation label
        self.conversation_label = QLabel("New Conversation")
        self.conversation_label.setStyleSheet("font-style: italic; color: #666;")
        menu_layout.addWidget(self.conversation_label)
        
        main_layout.addLayout(menu_layout)

        # Chat Display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("""
            font-size: 14px; 
            background-color: #f8f9fa; 
            padding: 10px;
            border-radius: 5px;
        """)
        self.chat_display.setMinimumHeight(400)
        main_layout.addWidget(self.chat_display)

        # Input Area (Horizontal Layout)
        input_layout = QHBoxLayout()

        # User Input Field
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Type your message here...")
        self.user_input.setStyleSheet("""
            font-size: 14px; 
            padding: 8px;
            border-radius: 5px;
            border: 1px solid #ced4da;
        """)
        self.user_input.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.user_input, 6)  # Stretch factor of 6

        # Send Button
        self.send_button = QPushButton("Send")
        self.send_button.setStyleSheet("""
            font-size: 14px;
            padding: 8px;
            background-color: #007bff;
            color: white;
            border-radius: 5px;
        """)
        self.send_button.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_button, 1)  # Stretch factor of 1

        # Settings Button
        self.settings_button = QPushButton("⚙️")
        self.settings_button.setStyleSheet("""
            font-size: 16px;
            padding: 8px;
            border-radius: 5px;
        """)
        self.settings_button.setToolTip("Settings")
        self.settings_button.clicked.connect(self.open_settings)
        input_layout.addWidget(self.settings_button, 1)  # Stretch factor of 1

        main_layout.addLayout(input_layout)

        # Status Bar
        self.status_bar = QLabel("Ready")
        self.status_bar.setStyleSheet("""
            font-size: 12px;
            color: #6c757d;
            padding: 5px;
        """)
        main_layout.addWidget(self.status_bar)

        self.setLayout(main_layout)
        
        # Load system prompt
        self.load_system_prompt()
        
        # Check for API keys and show warning if not set
        self.check_api_keys()

    def load_system_prompt(self):
        """Load system prompt from ai_guidance.ini"""
        try:
            guidance_config = configparser.ConfigParser()
            guidance_config.read(self.config.guidance_file)
            
            if 'AI_GUIDANCE' in guidance_config and 'system_prompt' in guidance_config['AI_GUIDANCE']:
                self.system_prompt = guidance_config['AI_GUIDANCE']['system_prompt']
        except Exception as e:
            print(f"Error loading system prompt: {e}")
            self.system_prompt = "You are a helpful assistant."

    def check_api_keys(self):
        """Check if API keys are set and show warning if not"""
        if not self.config.openai_api_key:
            self.status_bar.setText("Warning: OpenAI API key not set. Please go to Settings.")
            self.status_bar.setStyleSheet("font-size: 12px; color: #dc3545; padding: 5px;")

    def open_settings(self):
        """Open the settings dialog"""
        self.settings_dialog = SettingsDialog(self.config)
        self.settings_dialog.settings_updated.connect(self.on_settings_updated)
        self.settings_dialog.show()
    
    def on_settings_updated(self):
        """Handle settings update"""
        self.load_system_prompt()
        self.check_api_keys()
        if self.config.openai_api_key:
            self.status_bar.setText("Ready")
            self.status_bar.setStyleSheet("font-size: 12px; color: #6c757d; padding: 5px;")

    def new_conversation(self):
        """Start a new conversation"""
        # Confirm if there's unsaved data
        if self.chat_history and not self.current_conversation_file:
            reply = QMessageBox.question(
                self, 
                "Unsaved Conversation",
                "Do you want to save the current conversation before starting a new one?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Cancel:
                return
            elif reply == QMessageBox.StandardButton.Yes:
                if not self.save_conversation():
                    return  # User canceled the save dialog
        
        # Clear the chat history and display
        self.chat_history = []
        self.chat_display.clear()
        self.current_conversation_file = None
        self.conversation_label.setText("New Conversation")
        self.status_bar.setText("New conversation started")
    
    def save_conversation(self):
        """Save the current conversation"""
        if not self.chat_history:
            QMessageBox.information(self, "Information", "No conversation to save.")
            return False
        
        if self.current_conversation_file:
            # Save to the existing file
            return self.save_conversation_to_file(self.current_conversation_file)
        else:
            # No file yet, use Save As
            return self.save_conversation_as()
    
    def save_conversation_as(self):
        """Save the current conversation with a new name"""
        if not self.chat_history:
            QMessageBox.information(self, "Information", "No conversation to save.")
            return False
        
        # Get a title for the conversation
        title, ok = QInputDialog.getText(
            self, 
            "Conversation Title",
            "Enter a title for this conversation:",
            QLineEdit.EchoMode.Normal,
            "Conversation " + datetime.now().strftime("%Y-%m-%d")
        )
        
        if not ok or not title:
            return False  # User canceled
        
        # Create a filename from the title
        filename = title.replace(' ', '_').replace(':', '-').replace('/', '-')
        file_path = self.config.context_dir / f"{filename}.json"
        
        # Check if file exists
        if file_path.exists():
            reply = QMessageBox.question(
                self, 
                "File Exists",
                "A file with this name already exists. Overwrite?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                return self.save_conversation_as()  # Try again
        
        return self.save_conversation_to_file(file_path, title)
    
    def save_conversation_to_file(self, file_path, title=None):
        """Save the conversation to a specific file"""
        try:
            # Create conversation data structure
            conversation_data = {
                "title": title or Path(file_path).stem,
                "date": datetime.now().isoformat(),
                "system_prompt": self.system_prompt,
                "messages": self.chat_history
            }
            
            # Save to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(conversation_data, f, indent=2, ensure_ascii=False)
            
            self.current_conversation_file = file_path
            self.conversation_label.setText(conversation_data["title"])
            self.status_bar.setText(f"Conversation saved to {file_path}")
            return True
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save conversation: {str(e)}")
            return False
    
    def load_conversation(self):
        """Load a saved conversation"""
        dialog = LoadConversationDialog(self.config.context_dir)
        if dialog.exec():
            file_path = dialog.get_selected_file()
            if file_path and os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        conversation_data = json.load(f)
                    
                    # Check if the data has the expected structure
                    if "messages" not in conversation_data:
                        raise ValueError("Invalid conversation file format")
                    
                    # Clear current conversation
                    self.chat_history = []
                    self.chat_display.clear()
                    
                    # Load system prompt if available
                    if "system_prompt" in conversation_data:
                        self.system_prompt = conversation_data["system_prompt"]
                    
                    # Load messages
                    self.chat_history = conversation_data["messages"]
                    
                    # Update the display
                    for message in self.chat_history:
                        if message["role"] == "user":
                            self.chat_display.append(f'<div style="text-align: right;"><span style="background-color: #e9ecef; padding: 5px 10px; border-radius: 10px; display: inline-block;"><b>You:</b> {message["content"]}</span></div>')
                        elif message["role"] == "assistant":
                            self.chat_display.append(f'<div style="text-align: left;"><span style="background-color: #d1ecf1; padding: 5px 10px; border-radius: 10px; display: inline-block;"><b>{self.config.assistant_name}:</b> {message["content"]}</span></div>')
                    
                    # Update current file and label
                    self.current_conversation_file = file_path
                    self.conversation_label.setText(conversation_data.get("title", Path(file_path).stem))
                    self.status_bar.setText(f"Conversation loaded from {file_path}")
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Failed to load conversation: {str(e)}")

    def send_message(self):
        user_text = self.user_input.text().strip()
        if user_text:
            # Update UI
            self.chat_display.append(f'<div style="text-align: right;"><span style="background-color: #e9ecef; padding: 5px 10px; border-radius: 10px; display: inline-block;"><b>You:</b> {user_text}</span></div>')
            self.user_input.clear()
            self.status_bar.setText("AI is thinking...")

            # Add to chat history
            self.chat_history.append({"role": "user", "content": user_text})

            # Run OpenAI in a background thread
            self.ai_worker = OpenAIWorker(
                user_text, 
                self.config.openai_api_key,
                chat_history=self.chat_history,
                system_prompt=self.system_prompt
            )
            # Pass the config to the worker
            self.ai_worker.config = self.config
            self.ai_worker.response_signal.connect(self.display_ai_response)
            self.ai_worker.error_signal.connect(self.display_error)
            self.ai_worker.start()

    def display_ai_response(self, ai_text):
        """Handles AI response and triggers TTS."""
        # Update UI with custom assistant name
        self.chat_display.append(f'<div style="text-align: left;"><span style="background-color: #d1ecf1; padding: 5px 10px; border-radius: 10px; display: inline-block;"><b>{self.config.assistant_name}:</b> {ai_text}</span></div>')
        self.status_bar.setText("Ready")
        
        # Add to chat history
        self.chat_history.append({"role": "assistant", "content": ai_text})

        # Run ElevenLabs TTS in a background thread if enabled
        if self.config.tts_enabled:
            self.tts_worker = ElevenLabsWorker(
                ai_text, 
                self.config.elevenlabs_api_key,
                self.config.elevenlabs_voice_id
            )
            self.tts_worker.error_signal.connect(self.display_error)
            self.tts_worker.start()
    
    def display_error(self, error_msg):
        """Display errors in the status bar"""
        self.status_bar.setText(error_msg)
        self.status_bar.setStyleSheet("font-size: 12px; color: #dc3545; padding: 5px;")


# ================== RUN PYQT APPLICATION ===================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Use Fusion style for a modern look
    chatbot = ChatbotApp()
    chatbot.show()
    sys.exit(app.exec())
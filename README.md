# AI Chatbot with Text-to-Speech and Conversation Memory

A desktop chatbot application built with PyQt6 that interfaces with OpenAI's GPT models and ElevenLabs' text-to-speech API to create an interactive AI assistant with conversation memory.

## Features

- **Modern UI**: Clean, intuitive interface with chat bubbles and status indicators
- **AI Integration**: Uses OpenAI's GPT models (GPT-4 by default) for intelligent responses
- **Text-to-Speech**: Optional voice responses using ElevenLabs' realistic voice synthesis
- **Conversation Memory**: Save, load, and manage conversation history
- **Customization**:
  - Custom assistant name
  - Custom system prompts for controlling AI behavior and personality
  - Model selection (gpt-4, gpt-3.5-turbo, etc.)
  - Voice selection via ElevenLabs

## Screenshots

[Screenshots would be added here]

## Requirements

- Python 3.7+
- PyQt6
- OpenAI Python SDK
- Requests
- Playsound

## Installation

1. Clone this repository or download the source code:
   ```
   git clone https://github.com/yourusername/ai-chatbot.git
   cd ai-chatbot
   ```

2. Install the required dependencies:
   ```
   pip install PyQt6 openai requests playsound
   ```

3. Run the application:
   ```
   python chatbot.py
   ```

## Configuration

On first run, the application will create:

- A configuration file in your home directory (`~/.chatbot_config.ini`)
- A system prompt file in the application directory (`ai_guidance.ini`)
- A directory for storing conversations (`chat_contexts/`)

### API Keys

You'll need to provide:

1. **OpenAI API Key**: Get one from [OpenAI's platform](https://platform.openai.com/)
2. **ElevenLabs API Key** (optional for TTS): Get one from [ElevenLabs](https://elevenlabs.io/)
3. **ElevenLabs Voice ID** (optional for TTS): The ID of the voice you want to use

These can be entered in the Settings dialog accessed via the gear icon.

## Usage

### Basic Chat

1. Type your message in the input field and press Enter or click Send
2. The AI will respond in the chat area
3. If text-to-speech is enabled, the response will also be spoken

### Conversation Management

- **New Conversation**: Click File → New Conversation
- **Save Conversation**: Click File → Save Conversation
- **Save As**: Click File → Save Conversation As...
- **Load Conversation**: Click File → Load Conversation

### Customization

Click the gear icon to access settings:

- **API Keys**: Enter your OpenAI and ElevenLabs credentials
- **Assistant Name**: Customize your AI assistant's name
- **Model Selection**: Choose which OpenAI model to use
- **Text-to-Speech**: Toggle voice responses on/off
- **System Prompt**: Edit the AI's instructions and personality

### System Prompt

The system prompt controls your AI assistant's behavior, knowledge, and personality. Edit this in the settings to customize how your assistant responds.

Example:

```
You are a helpful assistant named Luna. You have expertise in programming and science.
Please respond in a friendly, conversational tone, and keep your answers concise unless I ask for details.
Feel free to use analogies to explain complex concepts.
```

## File Structure

- `chatbot.py`: Main application file
- `ai_guidance.ini`: Contains the system prompt
- `chat_contexts/`: Directory for saved conversations
- `~/.chatbot_config.ini`: User configuration file
- `~/.chatbot_temp/`: Temporary directory for audio files

## Advanced Usage

### Customizing the AI's Personality

Edit the system prompt in settings to give the AI specific instructions about how to respond. You can:

- Specify knowledge areas or expertise
- Set the tone and style of responses
- Define specific behaviors or constraints
- Create role-playing scenarios

### Using Different Models

Change the model in settings to use different OpenAI models:

- `gpt-4`: Most capable model, best for complex tasks
- `gpt-3.5-turbo`: Faster and more economical for simpler interactions
- Also supports other models like `gpt-4-turbo` or `gpt-4-32k` if available

## Troubleshooting

- **API Key Issues**: Ensure your API keys are entered correctly in Settings
- **Text-to-Speech Not Working**: Verify your ElevenLabs credentials and voice ID
- **Application Crashes**: Check console output for error messages

## License

[Your license information here]

## Acknowledgments

- OpenAI for their GPT models
- ElevenLabs for their text-to-speech technology
- PyQt6 for the GUI framework

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

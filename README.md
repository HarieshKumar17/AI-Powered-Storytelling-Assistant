# AI-Powered Storytelling Assistant

## Project Overview

The AI-Powered Storytelling Assistant addresses the growing need for compelling storytelling across various professional and personal contexts. It democratizes access to high-quality narrative creation by combining artificial intelligence with professional expertise, making powerful storytelling accessible to everyone from business professionals to creative writers.

## Key Features

- **AI-Powered Story Generation**: Utilizes Groq's LLM API for generating customized stories
- **Multiple Story Types**: Supports various narrative structures and creative enhancements
- **Professional Consultation**: Built-in booking system for professional storytellers
- **User Management**: Secure authentication and story management system
- **Multi-format Export**: Download stories in TXT, DOCX, and PDF formats
- **Story Parameters Customization**: Extensive options for story customization
- **Story Library**: Save and manage multiple stories

## Core Functionalities

### Story Generation

- Customizable parameters including:
    - Story origin (Personal/Well-known Tale)
    - Use case
    - Time frame
    - Focus areas
    - Narrative structure
    - Creative enhancements
- AI-powered content generation using Groq API
- Support for story editing and refinement

### Installation and Setup

1. **Prerequisites**
    
    ```bash
    pip install -r requirements.txt
    ```
    
2. **Environment Variables(.env)**
    
    ```
    GROQ_API_KEY=your_groq_api_key
    ```
    
3. **Requirements.txt**
    
    ```
    streamlit
    python-dotenv
    groq
    werkzeug
    requests
    python-docx 
    reportlab
    openpyxl
    ```
    

## API Integration

### Groq API Integration

```python
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_story(data, selected_tale_text=None):
    prompt = construct_prompt(data, selected_tale_text)
    response = groq_client.chat.completions.create(
        messages=[
            {"role": "system", "content": "You are an AI storytelling assistant."},
            {"role": "user", "content": prompt}
        ],
        model="llama-3.1-70b-versatile",
    )
    return response.choices[0].message.content

```

### Running the Chatbot

Run the Streamlit application with the following command:

```
streamlit run app.py
```

## Contributing

Contributions are welcome! Please read our contributing guidelines and code of conduct before submitting pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

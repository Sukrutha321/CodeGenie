# CodeGenie Setup Guide

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Create Project Structure
```bash
mkdir templates
mv login.html templates/
mv homepage.html templates/
```

### 3. Set API Token (Optional)
```bash
# Windows
set HUGGINGFACE_API_TOKEN=your_token_here

# Mac/Linux
export HUGGINGFACE_API_TOKEN=your_token_here
```

### 4. Run Application
```bash
python app.py
```

### 5. Access in Browser
```
http://localhost:5000
```

## Default Login

Email: `demo@codegenie.dev`
Password: `Demo2024!`

You can also create your own account using the signup form.

## Features

- User authentication (login/signup)
- Multi-language code generation (Python, JavaScript, Java, C++)
- Natural language to code conversion
- Code explanation
- Copy to clipboard
- Clean, modern interface

## API Endpoints

- `GET /` - Login page
- `GET /homepage` - Main application (requires login)
- `POST /api/login` - User authentication
- `POST /api/signup` - User registration
- `POST /api/generate` - Generate code from prompt
- `POST /api/logout` - End session

## Notes

- Passwords must be at least 8 characters
- Users are stored in memory (restart clears data)
- For production, implement database and password hashing
- Hugging Face token required for AI code generation

## Troubleshooting

**Port already in use**: Change port in `app.py`
**Template not found**: Ensure HTML files are in `templates/` folder
**Import errors**: Run `pip install -r requirements.txt`

## Technology Stack

- Frontend: HTML, CSS, JavaScript
- Backend: Python (Flask)
- AI: Hugging Face API
- Storage: In-memory (replace with database for production)

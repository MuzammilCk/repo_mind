# 🧠 Repo Mind (MVP for Testing)

Hey! This is the autonomous agent we built before the pivot. It uses Gemini 3 + GitHub API to find projects and generate code.

## 🚀 How to Run It

1. **Install Dependencies**:
   ```bash
   pip install fastapi uvicorn google-genai pydantic python-multipart PyGithub radon pylint
   ```

2. **Set API Keys**:
   Make sure you have these environment variables set (or in a `.env` file):
   - `GEMINI_API_KEY`: Your Google AI Studio key
   - `GITHUB_TOKEN`: Your GitHub Personal Access Token

3. **Start the Server**:
   ```bash
   python -m uvicorn main:app --reload
   ```

4. **Use the Agent**:
   - Open your browser to: `http://localhost:8000`
   - You'll see the "Repo Mind" interface
   - Enter a goal like: *"Find a Python PDF library and build a POC"*
   - Watch it plan, execute tools, and verify results!

## 🧪 What to Test

Try these prompts:
- "Find a React state management library that isn't Redux and show me a counter example"
- "Analyze the 'requests' library repository and tell me its main dependencies"
- "Find a Go web framework and write a Hello World server"

## ⚠️ Known Issues
- It might hit the 5 RPM rate limit if the plan is too long (that's why we added the "Macro-Planning" feature)
- If it gets stuck, just refresh and try a simpler prompt.

Happy breaking! 💥

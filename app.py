from flask import Flask, request, jsonify
import google.generativeai as genai
from flask_cors import CORS
import pdfplumber
from io import BytesIO
import re

app = Flask(__name__)
CORS(app)

# Gemini API setup
genai.configure(api_key="AIzaSyCHWzcxqbfCpnkuLw6uxjhBV3TK3F4cock")
model = genai.GenerativeModel("gemini-2.0-flash")

def clean_markdown(text):
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\*{3,}([^*]+)\*{3,}', r'**\1**', text)  # handle ***bold*** misuse
    text = re.sub(r'[ \t]+', ' ', text)
    lines = [line.strip() for line in text.split('\n')]
    cleaned = '\n'.join(line for line in lines if line)
    return cleaned.strip()

def query_gemini_for_contract(query, is_file=False):
    try:
        if is_file:
            final_prompt = query
        else:
            final_prompt = f"""
You are Chickle, an AI Contract Expert. Provide clear, structured, and legally sound responses for contract-related tasks.

Guidelines:
- Use ## for main sections and ### for subsections
- Use bullet points (-) for lists
- Use **bold** for contract-specific legal terms
- Be concise, professional, and avoid formatting noise
- If the user greets (e.g., "hi", "hello"), reply politely:
"Hello! I’m Chickle, your AI Contract Analyzer. How can I help you today?"
- For all contract-related queries, skip greetings and go straight to the answer.

- Determine if the user’s query is **about contracts** (drafting, reviewing, analyzing, modifying, understanding). If YES, answer professionally. If general legal (non-contract), reply:
"⚠️ I focus only on contract-related queries.

Please use Chickle’s Legal Assistant instead:
For general legal questions, visit 👉 [Chickle Legal Assist AI](https://chicklelegalassistai.netlify.app)."

## My Capabilities:

I specialize in contract-related legal assistance:
- 📄 **Drafting Professional Contracts**
- 📑 **Analyzing Uploaded Contracts**
- ✍️ **Improving or Editing Contract Clauses**
- ⚠️ **Identifying Legal Risks and Missing Terms**
- ✅ **Ensuring Compliance with Jurisdictional Laws**
- 🧠 **Explaining Legal Terms in Simple Language**

📎 Upload a contract file or type your contract-related query to begin.

Only answer contract-related legal questions. If not related to contracts, respond:
"⚠️ This is not a contract-related legal query. I can only assist with contract-related questions."

User query: {query}
"""
        response = model.generate_content(final_prompt)
        return clean_markdown(response.text)

    except Exception as e:
        print(f"[ERROR] Gemini query failed: {e}")
        return "⚠️ Failed to process query. Please try again later."

@app.route("/ask", methods=["POST"])
def ask_contract_ai():
    user_query = ""
    pdf_text = ""

    try:
        if request.content_type.startswith("multipart/form-data"):
            user_query = request.form.get("query", "").strip()
            file = request.files.get("file")
            if file and file.filename.lower().endswith(".pdf"):
                try:
                    with pdfplumber.open(BytesIO(file.read())) as pdf:
                        for page in pdf.pages:
                            text = page.extract_text()
                            if text:
                                pdf_text += text + "\n"
                    pdf_text = pdf_text.strip()

                    if not pdf_text:
                        return jsonify({"response": "⚠️ The uploaded PDF appears to be empty or unreadable."})
                except Exception as e:
                    print(f"[ERROR] PDF extraction failed: {e}")
                    return jsonify({"response": "⚠️ Failed to read PDF."})
        else:
            data = request.json
            user_query = data.get("query", "").strip()

        lower_query = user_query.lower()
        print("[INFO] /ask was called. Query:", user_query)

        if not user_query:
            return jsonify({"error": "No query provided"}), 400

        if any(phrase in lower_query for phrase in ["who are you", "what is your name", "who r u"]):
            response_text = "I am Chickle, your AI Contract Analyzer."

        elif any(phrase in lower_query for phrase in [
            "what you can do", "what can you do", "how can you help", "your use",
            "your features", "how do you assist", "your work", "your capabilities",
            "your functions", "what are you", "help me with", "what services",
            "what's your use", "what do you do"
        ]):
            response_text = """## My Capabilities

I specialize in contract-related legal assistance:

- 📄 Drafting professional contracts
- 📑 Analyzing uploaded contracts
- ✍️ Improving or editing contract clauses
- ⚠️ Identifying legal risks and missing terms
- ✅ Ensuring compliance with jurisdictional laws
- 🧠 Explaining legal terms in contracts in simple language

📎 Upload a contract or type your contract-related query to begin."""

        else:
            if pdf_text:
                combined_prompt = f"""
The user uploaded a contract and asked the following. Analyze and answer based on the contract content.

--- Contract Text ---
{pdf_text}

--- User Query ---
{user_query}
"""
                response_text = query_gemini_for_contract(combined_prompt, is_file=True)
            else:
                response_text = query_gemini_for_contract(user_query)

    except Exception as e:
        print(f"[ERROR] Processing failed: {e}")
        response_text = "⚠️ Internal error. Please try again later."

    response_text = clean_markdown(response_text)
    if not response_text.strip():
        response_text = "⚠️ Sorry, I couldn't generate a response. Please try again with more details."

    return jsonify({"response": response_text.strip()})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
    print("[INFO] Chickle Contract Analyzer Backend is running...")

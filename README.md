# Metamorphosis_Agent
♻️ Metamorphosis Agent

Turn your discarded items into upcycled treasures using AI.

Metamorphosis Agent is an AI-powered application that analyzes images of waste (like plastic bottles, cardboard, or old furniture) and generates creative DIY upcycling blueprints. It uses Google Gemini 2.0 Flash for visual analysis and material identification, and Stable Diffusion XL (via Hugging Face) to visualize the final upcycled product.

✨ Features

👁️ Visual Analysis: Automatically identifies waste materials from uploaded photos.

📝 Smart Blueprints: Generates step-by-step assembly guides and material lists.

🎨 AI Visualization: Creates photorealistic concept images of what the final product could look like.

⚡ Real-time Processing: Fast analysis and generation using the latest AI models.

🛠️ Tech Stack

Frontend: Streamlit

Vision/Text AI: Google Gemini 2.0 Flash

Image Generation: Stable Diffusion XL (via Hugging Face Inference API)

Language: Python 3.10+

🚀 Installation

Clone the repository

git clone [https://github.com/your-username/Metamorphosis_Agent.git]
cd Metamorphosis_Agent


Install dependencies

pip install -r requirements.txt


Set up environment variables
Create a .env file in the root directory and add your API keys:

GEMINI_API_KEY=your_google_gemini_key
HF_TOKEN=your_hugging_face_token


🏃‍♂️ Usage

Run the application locally:

streamlit run metamorphosis_agent.py


The app will open in your browser at http://localhost:8501.

📂 Project Structure

Metamorphosis_Agent/
├── metamorphosis_agent.py  # Main application logic
├── requirements.txt        # Python dependencies
├── .env                    # API keys (Do NOT commit this to GitHub)
├── .gitignore              # Files to ignore (e.g., .env, __pycache__)
└── README.md               # Project documentation


🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

📄 License

This project is open-source and available under the MIT License."# Metamorphosis_Agent" 

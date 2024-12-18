# **DocuFix AI: Document-Based Assistance for Repair-Focused Solutions**

DocuFix AI is a multi-agent system designed to revolutionize automotive DIY repair by combining Retrieval-Augmented Generation (RAG) with agent-based orchestration. The system provides users with accurate, contextually grounded repair guidance through document-based assistance. With an interactive interface, DocuFix provides safe, effective, and accessible solutions for complex repair tasks.  

[![Next][Next.js]][Next-url]
[![Flask][Flask]][Flask-url]
[![OpenAI][OpenAI]][OpenAI-url]

## **Setup**  
Follow the steps below to set up and run DocuFix AI locally.  

### **Clone the Repository**  
```bash  
git clone https://github.com/dotref/docufix-ai.git
cd docufix-ai  
```  

### **Frontend**  
Run the frontend in a new terminal:  
```bash  
cd frontend  
npm install  
npm run dev  
```  

### **Backend**  
Run the backend in another terminal:  
```bash  
cd backend  
pip install -r requirements.txt  
python app.py  
```  

### **Data Storage**  
Currently, all data is stored locally in the `backend/data` directory.  

## **How It Works**  
1. **Upload Repair Documents:** Users can upload automotive manuals in PDF or TXT format for document indexing and retrieval.  
2. **Ask a Query:** Users enter repair-related questions into the chat interface.  
3. **Receive Guidance:** DocuFix provides clear, step-by-step instructions, explanations of technical terms, and a checklist of necessary tools.  

## **Contributions**  
This project leverages **LlamaIndex** for document indexing and retrieval and **AutoGen** for multi-agent coordination. 

[Next.js]: https://img.shields.io/badge/next.js-000000?style=for-the-badge&logo=nextdotjs&logoColor=white
[Next-url]: https://nextjs.org/
[Flask]: https://img.shields.io/badge/Flask-000000.svg?style=for-the-badge&logo=Flask&logoColor=white
[Flask-url]: https://flask.palletsprojects.com/en/stable/
[OpenAI]: https://img.shields.io/badge/OpenAI-412991.svg?style=for-the-badge&logo=OpenAI&logoColor=white
[OpenAI-url]: https://openai.com/

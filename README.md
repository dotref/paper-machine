# paper-machine
## rag-skeleton setup

1. install dependencies
- `python3 -m pip install -r requirements.txt`
2. populate `./data`
- `python3 data.py` will populate the `./data` folder with text files.
3. run
- make sure OpenAI API key is set: `os.environ['OPENAI_API_KEY'] = "sk-..."`
- `python3 main.py` will start a command line interface to input queries. The program will output relevant chunks of text along with their file path and relvancy score. 
- Type `q` to quit the program.
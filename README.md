# paper-machine
## rag-skeleton
- `main.py` contains a RAG workflow that supports the following actions:
1. adding documents to the index.
2. removing documents from the index.
3. using the index and a query to retrieve relevant sentences.

## setup

1. install dependencies
- `python3 -m pip install -r requirements.txt`
2. populate `./data`
- `python3 data.py` will populate the `./data` folder with text files.
3. run
- make sure OpenAI API key is set: `os.environ['OPENAI_API_KEY'] = "sk-..."`
- in the `test()` method, fill out the absolute filepath(s) of documents you wish to delete.
- `python3 main.py` run an example sequence of actions. It will
    - insert documents from the `./data` directory into the index.
    - run a query, printing the retrieved sentences and their retrieval scores.
    - remove the specified documents from the index.
    - run the query again (deleting documents relevant to the query should cause retrieval scores to go down).
# paper-machine
## rag-skeleton
- `main.py` contains functions for creating/loading/deleting individual indices for each uploaded document RAG router query engine demo.
- creation and storage of indices is slow. The idea is that during a user session, indices will be loaded once at the beginning and stored once at the end, persisting any new document indices that were created during the user session in the storage context. OR MongoIndexStore support automatic persistence (need to setup MongoDB stuff).

## setup

1. install dependencies
- `python3 -m pip install -r requirements.txt`
2. populate `./data`
- `python3 data.py` will populate the `./data` folder with text files.
3. run
- make sure OpenAI API key is set in `.env` file in root dir.
- `python3 main.py` run a RAG demo. It will:
    - create an index for each document from the `./data` folder and persist it in `./storage`.
    - demonstrate query routing.
    - run queries, printing the llm generated response and retrieved source nodes.

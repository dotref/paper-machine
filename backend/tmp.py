from llama_index.core import Document, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter, SentenceWindowNodeParser

class RAGWithDifferentParsers:
    def __init__(self):
        self.document = Document(
            text="""
            The Python programming language was created by Guido van Rossum. 
            It was first released in 1991. Python is known for its simplicity 
            and readability. The language emphasizes code readability with its 
            notable whitespace indentation. Python features a dynamic type system 
            and automatic memory management. It supports multiple programming 
            paradigms. These include procedural, object-oriented, and functional 
            programming. Python's comprehensive standard library is often cited 
            as one of its greatest strengths.
            """
        )
    
    def demonstrate_sentence_splitter(self):
        """
        Use case: When you need to control chunk sizes for API limits
        or want simple, size-based splitting
        """
        parser = SentenceSplitter(
            chunk_size=100,
            chunk_overlap=20
        )
        
        nodes = parser.get_nodes_from_documents([self.document])
        
        print("\n=== SentenceSplitter Example ===")
        print("Good for: API limits, size control")
        for i, node in enumerate(nodes):
            print(f"\nChunk {i+1} ({len(node.text)} chars):")
            print(node.text)
    
    def demonstrate_window_parser(self):
        """
        Use case: When you need contextual understanding and
        relationship between sentences
        """
        parser = SentenceWindowNodeParser(
            window_size=3,  # Each chunk contains 3 sentences
            window_metadata_key="window"
        )
        
        nodes = parser.get_nodes_from_documents([self.document])
        
        print("\n=== SentenceWindowNodeParser Example ===")
        print("Good for: Maintaining context, sentence relationships")
        for i, node in enumerate(nodes):
            print(f"\nWindow {i+1}:")
            print(node.text)
            print("Window Info:", node.metadata.get("window"))

# Example usage
def main():
    rag = RAGWithDifferentParsers()
    
    # Scenario 1: Token limit concerns
    print("\nScenario 1: Working with API token limits")
    rag.demonstrate_sentence_splitter()
    
    # Scenario 2: Need contextual understanding
    print("\nScenario 2: Need to maintain sentence context")
    rag.demonstrate_window_parser()

if __name__ == "__main__":
    main()
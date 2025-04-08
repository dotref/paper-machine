# Paper Machine System Diagrams

This directory contains a comprehensive set of system diagrams for the Paper Machine project, created using Mermaid. These diagrams provide visual representations of various aspects of the system architecture, data flow, and user interactions.

## Available Diagrams

1. **System Overview Diagram** ([system_diagram.md](system_diagram.md))
   - A high-level view of the entire system
   - Shows all major components and their relationships
   - Includes frontend, backend, and storage subsystems

2. **Simplified System Diagram** ([simplified_system_diagram.md](simplified_system_diagram.md))
   - Condensed version of the system diagram for presentations and posters
   - Focuses on key components and main interactions
   - Uses larger, bolder styling for better visibility from a distance

3. **RAG Flow Diagram** ([rag_flow_diagram.md](rag_flow_diagram.md))
   - Sequence diagram showing the RAG (Retrieval Augmented Generation) process
   - Illustrates document upload, embedding creation, and the query process
   - Shows interactions between services during the RAG workflow

4. **Deployment Diagram** ([deployment_diagram.md](deployment_diagram.md))
   - Docker-based deployment architecture
   - Container relationships and network connections
   - External service integrations

5. **User Workflow Diagram** ([user_workflow_diagram.md](user_workflow_diagram.md))
   - User journey through the system
   - Authentication, document management, and chat interaction flows
   - Decision points and process sequences

6. **Data Model Diagram** ([data_model_diagram.md](data_model_diagram.md))
   - Database entity relationships
   - Key data structures and their relationships
   - Storage model for users, files, embeddings, and chat data

## Styling

All diagrams use an enhanced color palette with improved contrast for better readability. The color scheme maintains visual differentiation between components while ensuring text remains clearly visible against background colors.

## How to View

These diagrams are in Mermaid syntax. You can view them:

1. Directly in GitHub or any other viewer that supports Mermaid rendering
2. Using the [Mermaid Live Editor](https://mermaid.live/) by copying the content
3. With VS Code using a Mermaid preview extension

## Diagram Update Process

When the system architecture changes, these diagrams should be updated to reflect the current state:

1. Identify which diagram(s) need updating
2. Modify the appropriate `.md` file with the new Mermaid syntax
3. Verify the diagram renders correctly
4. Commit the changes to version control 
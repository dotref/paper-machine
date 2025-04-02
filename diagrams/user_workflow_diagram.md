```mermaid
flowchart TD
    %% Start point
    Start([Start]) --> Login{User<br/>Logged In?}
    
    %% Authentication flow
    Login -->|No| RegisterOrLogin[Register/Login Page]
    RegisterOrLogin -->|Register| Register[Create Account<br/>Form]
    RegisterOrLogin -->|Login| LoginForm[Login Form]
    Register --> LoginForm
    LoginForm --> Dashboard
    
    %% Already logged in
    Login -->|Yes| Dashboard[Home Dashboard]
    
    %% Home Dashboard actions
    Dashboard --> BrowseFiles[Browse Files]
    Dashboard --> UploadNew[Upload New Document]
    Dashboard --> StartChat[Start New Chat]
    Dashboard --> ManageFolders[Manage Folders]
    
    %% File operations
    BrowseFiles --> ViewFile[View Document]
    BrowseFiles --> DeleteFile[Delete Document]
    ViewFile --> ChatWithDoc[Chat With Document]
    UploadNew --> Processing{Processing<br/>Required?}
    Processing -->|Yes| CreateEmbeddings[Create Embeddings]
    Processing -->|No| DocumentReady[Document Ready]
    CreateEmbeddings --> DocumentReady
    
    %% Folder operations
    ManageFolders --> CreateFolder[Create Folder]
    ManageFolders --> OrganizeFiles[Organize Files]
    
    %% Chat operations
    StartChat --> SelectDocs[Select Documents for Context]
    ChatWithDoc --> SelectDocs
    SelectDocs --> AskQuestion[Ask Question]
    AskQuestion --> RAGProcess[RAG Processing]
    RAGProcess --> ShowResponse[Show AI Response<br/>with Sources]
    ShowResponse --> ViewSource[View Source Document]
    ShowResponse --> AskFollowup[Ask Follow-up Question]
    AskFollowup --> RAGProcess
    
    %% Style definitions - Improved color contrast
    classDef start fill:#e680ff,stroke:#330033,stroke-width:2px,color:#330033
    classDef process fill:#80b3ff,stroke:#003380,stroke-width:1px,color:#001a40
    classDef io fill:#99e699,stroke:#006600,stroke-width:1px,color:#003300
    classDef decision fill:#ffcc66,stroke:#cc7700,stroke-width:1px,color:#663d00
    classDef end fill:#a6a6a6,stroke:#333333,stroke-width:1px,color:#1a1a1a
    
    %% Apply styles
    class Start start
    class Dashboard,BrowseFiles,UploadNew,StartChat,ManageFolders,ViewFile,DeleteFile,ChatWithDoc,CreateEmbeddings,DocumentReady,CreateFolder,OrganizeFiles,SelectDocs,AskQuestion,ShowResponse,ViewSource,AskFollowup process
    class RegisterOrLogin,Register,LoginForm io
    class Login,Processing decision
    class RAGProcess process
``` 
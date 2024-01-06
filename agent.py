# -*- coding: utf-8 -*-
import json
import sys
import warnings
from pydantic import BaseModel, Field

from langchain.agents import Tool, initialize_agent
from langchain.chains import RetrievalQA
from langchain_community.chat_models import ChatOpenAI
# from langchain_community.embeddings.openai import OpenAIEmbeddings
from langchain.embeddings.langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import DocArrayInMemorySearch
from langchain_community.tools import ShellTool, DuckDuckGoSearchRun
from langchain.schema import HumanMessage, SystemMessage, AIMessage


class ConfigLoader:
    def __init__(self, config_filename='config.json'):
        self.config_filename = config_filename
        self.config = self.load_config()
        if self.config['openai']['api_key']=='':
            self.config['openai']['api_key']=input("Please enter your OpenAI API key: ")

    def load_config(self):
        with open(self.config_filename, 'r') as file:
            return json.load(file)


class DocumentProcessor:
    def __init__(self, config):
        self.config = config

    def process_documents(self):
        context_path = self.config['context']['path']
        loader = DirectoryLoader(context_path, glob="*", loader_cls=TextLoader)
        docs = loader.load()
        embeddings = OpenAIEmbeddings(openai_api_key=self.config['openai']['api_key'])
        text_splitter = RecursiveCharacterTextSplitter()
        documents = text_splitter.split_documents(docs)
        vector = DocArrayInMemorySearch.from_documents(documents, embeddings)
        return vector.as_retriever()


class ChatAgent:
    def __init__(self, config, retriever):
        self.config = config
        self.retriever = retriever
        self.agent = self.initialize_agent()

    def initialize_agent(self):
        llm = ChatOpenAI(
            openai_api_key=self.config['openai']['api_key'],
            model=self.config['openai']['model'],
            temperature=self.config['openai']['temperature']
        )

        tools = [
            Tool(
                args_schema=DocumentInput,
                name='Additional context',
                description="Additional context that has been provided by user",
                func=RetrievalQA.from_chain_type(llm=llm, retriever=self.retriever),
            ),
            ShellTool(),
            DuckDuckGoSearchRun()
        ]

        return initialize_agent(tools, llm, agent='chat-conversational-react-description', 
                                verbose=True, handle_parsing_errors=True)

    def run(self):
        chat_history = []
        # Add a system message to the chat history
        system_message = 'You are a chatbot, that can run tools. Please be confident. Try to solve task until you solve it or you are stuck.'
        chat_history.append(SystemMessage(content=system_message))
        while True:
            user_input = input("You: ")
            if user_input.lower() in ['exit', 'quit']:
                break
            
            # Update the chat history with the User input
            chat_history.append(HumanMessage(content=user_input))

            response = self.agent.run(input=user_input, chat_history=chat_history)
            
            # Update the chat history with the Agent response
            chat_history.append(AIMessage(content=response))


class DocumentInput(BaseModel):
    question: str = Field()


def main():
    if len(sys.argv) > 1:
        config_filename = sys.argv[1]
    else:
        config_filename = 'config.json'

    config_loader = ConfigLoader(config_filename)
    document_processor = DocumentProcessor(config_loader.config)
    retriever = document_processor.process_documents()

    chat_agent = ChatAgent(config_loader.config, retriever)
    warnings.filterwarnings('ignore', category=UserWarning)
    chat_agent.run()


if __name__ == '__main__':
    main()

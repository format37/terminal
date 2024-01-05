# -*- coding: utf-8 -*-
import paramiko
import time
import json
import datetime
import os
import sys
import tiktoken
# from openai import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import TextLoader
import re


def token_counter(text, model):
    try:        
        enc = tiktoken.encoding_for_model(model) 
        tokens = enc.encode(text)
    except Exception as e:
        return str(e)
    return len(tokens)


def text_chat_gpt(api_key, model, messages, temperature=0.9):
    try:
        client = OpenAI(api_key=api_key)
        chat_completion = client.chat.completions.create(
            messages=messages,
            model=model,
        )
        return chat_completion
    
    except Exception as e:
        return str(e)
    

def save_message(prompt):
    folder = 'memory/'
    # Create folder if not exists
    if not os.path.exists(folder):
        os.makedirs(folder)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    filename = f'{folder}{timestamp}.txt'
    with open(filename, 'w') as f:
        f.write(prompt)

    
def extract_and_merge_codeblocks(message):
    """
    Extracts and merges all code blocks from the given message.

    Args:
    message (str): The message containing code blocks.

    Returns:
    tuple: A tuple containing the message text and the merged code text.
    """
    # Splitting the message using triple backticks as the delimiter
    parts = message.split("```")

    # Initializing variables to hold message text and code text
    message_text = ""
    code_text = ""

    # Iterating over the parts to separate message text and code text
    for i, part in enumerate(parts):
        if i % 2 == 0:
            # Even index parts are message text
            message_text += part
        else:
            # Odd index parts are code blocks
            code_text += part + "\n"  # Adding a newline for separation between code blocks

    return message_text.strip(), code_text.strip()


def extract_prompt_identifier(ssh_response):
    last_line = ssh_response.splitlines()[-1].strip()
    match = re.search(r'\S+@\S+(?=\s|:)', last_line)
    if match:
        return match.group()
    else:
        return None
    

def send_command(channel, cmd, config, timeout=0.1):
        # crop left and right \n if exists, using regex
        cmd = re.sub(r'^\n+|\n+$', '', cmd)
        print("Sending command:", cmd+"\n")
        channel.send(cmd + '\n')
        time.sleep(config['ssh']['sleep'])
        while not channel.recv_ready():
            time.sleep(timeout)
        return channel.recv(4096).decode('utf-8')
    

def send_command_and_wait(channel, cmd, ssh_prompt):
    cmd = cmd.replace('\\n', '')
    print("# Sending command:", cmd+"\n")
    # Send the command to the channel
    channel.send(cmd + '\n')
    
    # Buffer to store the received data
    output_buffer = ""
    
    # Wait for the command to complete (i.e., the prompt to reappear)
    while not ssh_prompt in output_buffer:
        # Check if the channel received data
        if channel.recv_ready():
            # Receive data and decode it
            output = channel.recv(4096).decode('utf-8')
            output_buffer += output
        else:
            # Wait before checking again
            print("Waiting for the server to respond. output_buffer:", output_buffer)
            time.sleep(1)

    return output_buffer


def send_interrupt(channel):
    channel.send(chr(0x03))  # Sending Ctrl-C
    time.sleep(1)
    

def main():
    # Read config from json
    if len(sys.argv) > 1:
        # Iterate over the arguments (excluding the script name)
        for i, arg in enumerate(sys.argv[1:]):
            print(f"Argument {i+1}: {arg}")
        config_filename = sys.argv[1]
    else:
        config_filename = 'config.json'
    with open(config_filename, 'r') as f:
        config = json.load(f)

    chat = ChatOpenAI(
        model=config['openai']['model'], 
        temperature=config['openai']['temperature'],
        openai_api_key=config['openai']['api_key']
        )

    # Starting the SSH session
    hostname = config['ssh']['address']
    port = config['ssh']['port']
    username = config['ssh']['username']
    password = config['ssh']['password']

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname, port, username, password)
    channel = client.invoke_shell()

    api_key = config['openai']['api_key']
    model = config['openai']['model']
    # Read system text from txt file
    with open('system.txt', 'r') as f:
        system_text = f.read()
    system_text += f"\nuser login: {username}"
    system_text += f"\nuser password: {password}"

    init_messages = []

    assistant_message = """Connecting to the server.
    ```:```"""
    init_messages.append (assistant_message)
    
    assistant_message = """Let's start from taking the sudo previleges.
    ```sudo date```"""
    init_messages.append (assistant_message)

    assistant_message = f"""Inputing the password.
    ```{config['ssh']['password']}```"""
    init_messages.append (assistant_message)

    messages = []
    messages.append(SystemMessage(content=system_text))

    for message in init_messages:
        
        messages.append(AIMessage(content=message))
        print("+ Assistant message:", message)
        text_block, code_block = extract_and_merge_codeblocks(message)
        
        ssh_response = send_command(channel, code_block, config, 3)
        print(f'bash: {ssh_response}')
        messages.append(HumanMessage(content=f"bash: {ssh_response}"))
        print(f"+ User content: bash: {ssh_response}")

    message = "Root access granted. How can I help you?"
    messages.append(AIMessage(content=message))
    assistant_message = {
        "message": message,
        "command": ""
    }
    print("Assistant message:", assistant_message)

    # Determine the current ssh identifier
    ssh_id = extract_prompt_identifier(ssh_response)

    while True:
        if assistant_message['command'] != "":
            command = assistant_message['command']
            if command.lower() == 'exit':
                ssh_response = "Session closed."
                break
            elif command.lower() == 'stop':
                send_interrupt()
                ssh_response = "Command interrupted."
            else:
                # ssh_response = send_command(channel, command, config)
                ssh_response = send_command_and_wait(channel, code_block, ssh_id)
            print(f'bash: {ssh_response}')
            # prompt.append({"role": "user", "content": f"bash: {ssh_response}"})
            messages.append(HumanMessage(content=f"bash: {ssh_response}"))
        else:
            user_text = input("Enter your message: ")
            if user_text.lower() == 'exit':
                ssh_response = "Session closed."
                break
            # prompt.append({"role": "user", "content": user_text})
            messages.append(HumanMessage(content=user_text))

        # Calculating the token count forecast
        
        # token_count = token_counter(str(prompt), model) # TODO: Restore token forecasting
        # print("Tokens forecast:", token_count)

        # Calling assistant
        response = str(chat(messages))
        
        print("response original:", response)
        messages.append(AIMessage(content=response))
        save_message(str(messages))
        try:
            text_block, code_block = extract_and_merge_codeblocks(response)
            assistant_message = {
                "message": text_block,
                "command": code_block
            }
        except Exception as e:
            print("Unable to parse codeblocks")
            assistant_message = {
                "message": assistant_message,
                "command": ""
            }

    channel.close()
    client.close()


if __name__ == '__main__':
    main()

# -*- coding: utf-8 -*-

import paramiko
import time
import requests
import json
import datetime
import os
import sys

def token_counter(text, model, address, port):
    url = f'http://{address}:{port}/token_counter'
    data = {
        "text": text,
        "model": model
    }
    # print('Token counter data:', data)
    response = requests.post(url, json=data)
    return response


def send_request(model, api_key, address, port, prompt):
    url = f'http://{address}:{port}/request'
    request_data = {
        "api_key": api_key,
        "model": model,
        "prompt": prompt
    }
    # Json dumps prompt
    prompt_dumped = json.dumps(prompt)
    print(
        'Token count forecast:', 
        token_counter(prompt_dumped, model, address, port).json()['tokens']
        )
    save_message(prompt_dumped)
    response = requests.post(url, json=request_data)
    return response


def save_message(prompt):
    folder = 'memory/'
    # Create folder if not exists
    if not os.path.exists(folder):
        os.makedirs(folder)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    filename = f'{folder}{timestamp}.txt'
    with open(filename, 'w') as f:
        f.write(prompt)


def parse_json_input(assistant_message):
    # Check and remove code block formatting if present
    if assistant_message.startswith("```json") and assistant_message.endswith("```"):
        print("Code block formatting detected.")
        # Removing the first 7 characters (```json\n) and the last 3 characters (```)
        assistant_message = assistant_message[7:-3].strip()

    # Parse the JSON string
    # try:
    parsed_json = json.loads(assistant_message)
    return parsed_json
    """except json.JSONDecodeError:
        # Handle the case where the string is not valid JSON
        return assistant_message"""
    
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

    # Starting the SSH session
    hostname = config['ssh']['address']
    port = config['ssh']['port']
    username = config['ssh']['username']
    password = config['ssh']['password']

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname, port, username, password)
    channel = client.invoke_shell()

    def send_command(cmd, config, timeout=0.1):
        channel.send(cmd + '\n')
        time.sleep(config['ssh']['sleep'])
        while not channel.recv_ready():
            time.sleep(timeout)
        return channel.recv(4096).decode('utf-8')

    def send_interrupt():
        channel.send(chr(0x03))  # Sending Ctrl-C
        time.sleep(1)

    openai_proxy_address = config['openai']['proxy']['address']
    openai_proxy_port = config['openai']['proxy']['port']
    api_key = config['openai']['api_key']
    model = config['openai']['model']
    # Read system text from txt file
    with open('system.txt', 'r') as f:
        system_text = f.read()
    system_text += f"\nuser login: {username}"
    system_text += f"\nuser password: {password}"

    prompt = [
        {"role": "system", "content": system_text},
        {"role": "user", "content": "Let's connect to the server and check the date."}
    ]

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

    for message in init_messages:
        prompt.append({"role": "assistant", "content": message})
        print("+ Assistant message:", message)
        # assistant_message = extract_and_merge_codeblocks(message)
        text_block, code_block = extract_and_merge_codeblocks(message)
        # command = assistant_message['command']
        ssh_response = send_command(code_block, config, 3)
        print(f'bash: {ssh_response}')
        prompt.append({"role": "user", "content": f"bash: {ssh_response}"})
        # print("+ User content:", f"bash: {ssh_response}")
        print(f"+ User content: bash: {ssh_response}")

    message = "Root access granted. How can I help you?"
    prompt.append({"role": "assistant", "content": message})
    assistant_message = {
        "message": message,
        "command": ""
    }
    print("Assistant message:", assistant_message)

    print('=== prompt:', prompt)

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
                ssh_response = send_command(command, config)
            print(f'bash: {ssh_response}')
            prompt.append({"role": "user", "content": f"bash: {ssh_response}"})
        else:
            user_text = input("Enter your message: ")
            if user_text.lower() == 'exit':
                ssh_response = "Session closed."
                break
            prompt.append({"role": "user", "content": user_text})

        # Calling assistant
        response = send_request(
            model, 
            api_key, 
            openai_proxy_address, 
            openai_proxy_port, 
            prompt
            )
        response_json = json.loads(response.json())
        try:
            assistant_message = response_json['choices'][0]['message']['content']
        except Exception as e:
            print("Error parsing assistant message:", e)
            print("Response text:", response.text)
            raise
        print("Assistant message:", assistant_message)
        # save_message(assistant_message, 'assistant')
        prompt.append({"role": "assistant", "content": assistant_message})
        # assistant_message = json.loads(assistant_message)
        try:
            text_block, code_block = extract_and_merge_codeblocks(assistant_message)
            assistant_message = {
                "message": text_block,
                "command": code_block
            }
            # print("Assistant blocks:", assistant_message)
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

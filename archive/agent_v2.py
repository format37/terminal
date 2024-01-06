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

    def send_command(cmd, config):
        channel.send(cmd + '\n')
        time.sleep(config['ssh']['sleep'])
        while not channel.recv_ready():
            time.sleep(0.1)
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
        {"role": "user", "content": "date"}
    ]

    assistant_message = {
        "message": "",
        "command": "date"
    }

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
        assistant_message = response_json['choices'][0]['message']['content']
        print("Assistant message:", assistant_message)
        # save_message(assistant_message, 'assistant')
        prompt.append({"role": "system", "content": assistant_message})
        # assistant_message = json.loads(assistant_message)
        try:
            assistant_message = parse_json_input(assistant_message)
        except Exception as e:
            print("Non-JSON message received.")
            assistant_message = {
                "message": assistant_message,
                "command": ""
            }

    channel.close()
    client.close()


if __name__ == '__main__':
    main()

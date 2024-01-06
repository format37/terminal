import paramiko
import time
import requests
import json
import datetime
import os

def token_counter(text, model, address):
    url = f'http://{address}/token_counter'
    data = {
        "text": text,
        "model": model
    }

    response = requests.post(url, json=data)
    return response


def send_request(model, api_key, address, prompt):
    url = f'http://{address}/request'
    request_data = {
        "api_key": api_key,
        "model": model,
        "prompt": prompt
    }
    # Json dumps prompt
    prompt_dumped = json.dumps(prompt)
    print(
        'Token count forecast:', 
        token_counter(prompt_dumped, model, address).json()['tokens']
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

def main():

    # Starting the SSH session
    # Replace with the appropriate hostname, port, username, password, and command
    # input address
    # hostname = input("Enter address (localhost): ")
    hostname = 'localhost'
    # input port
    # port = input("Enter port (2022): ")
    port = 2022
    # input username
    # username = input("Enter username: ")
    username = 'alex'
    # input password
    # password = input("Enter password: ")
    password = '3212321'


    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname, port, username, password)
    channel = client.invoke_shell()

    def send_command(cmd):
        channel.send(cmd + '\n')
        time.sleep(2)
        # if channel.recv_ready():
        while not channel.recv_ready():
            time.sleep(0.1)
        return channel.recv(4096).decode('utf-8')

    def send_interrupt():
        channel.send(chr(0x03))  # Sending Ctrl-C
        time.sleep(1)

    # openai_proxy_address = input("Enter OpenAI proxy address (localhost:4714): ")
    openai_proxy_address = '34.118.89.125:4714'
    # api_key = input('Please, input your Openai API key:')
    api_key = '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'
    # model = 'gpt-3.5-turbo-16k'
    model = 'gpt-4-1106-preview'
    # system_text = ""
    # Read system text from txt file
    with open('system.txt', 'r') as f:
        system_text = f.read()

    prompt = [
        {"role": "system", "content": system_text}
    ]

    assistant_message = "user:"  
        

    while True:

        # if assistant_message starts from user:
        if assistant_message.startswith('ssh:'):
            """command = input(
                "Enter command (type 'exit' to close session, ':' to update, 'stop' to interrupt): "
                )"""
            command = assistant_message[4:]
            if command.lower() == 'exit':
                ssh_response = "Session closed."
                break
            elif command.lower() == 'stop':
                send_interrupt()
                ssh_response = "Command interrupted."
                # print("Command interrupted.")
            else:
                ssh_response = send_command(command)
            print(f'SSH response: {ssh_response}')
            # save_message(ssh_response, 'ssh')
            prompt.append({"role": "user", "content": f"ssh answer: {ssh_response}"})
        elif assistant_message.startswith('wait:'):
            # Extract the count of seconds to wait
            seconds = int(assistant_message[5:])
            # Wait for the specified amount of seconds
            print(f"Waiting for {seconds} seconds...")
            time.sleep(seconds)
            print("Waiting done.")
            assistant_message = "ssh::"
            continue

        # elif assistant_message.startswith('user:'):
        else:
            user_text = input("Enter your message: ")
            prompt.append({"role": "user", "content": user_text})
            # save_message(user_text, 'user')

        response = send_request(model, api_key, openai_proxy_address, prompt)
        response_json = json.loads(response.json())
        assistant_message = response_json['choices'][0]['message']['content']
        print("Assistant message:", assistant_message)
        # save_message(assistant_message, 'assistant')
        prompt.append({"role": "system", "content": assistant_message})

    channel.close()
    client.close()


if __name__ == '__main__':
    main()

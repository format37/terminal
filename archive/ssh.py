import paramiko
import time

def ssh_session(hostname, port, username, password):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname, port, username, password)
    channel = client.invoke_shell()

    def send_command(cmd):
        channel.send(cmd + '\n')
        time.sleep(1)
        if channel.recv_ready():
            return channel.recv(4096).decode('utf-8')
        return ""

    def send_interrupt():
        channel.send(chr(0x03))  # Sending Ctrl-C
        time.sleep(1)

    while True:
        command = input(
            "Enter command (type 'exit' to close session, ':' to update, 'stop' to interrupt): "
            )
        if command.lower() == 'exit':
            break
        elif command.lower() == 'stop':
            send_interrupt()
            print("Command interrupted.")
        else:
            response = send_command(command)
            print(response)

    channel.close()
    client.close()


def main():
    # Replace with the appropriate hostname, port, username, password, and command
    # input address
    hostname = input("Enter address (localhost): ")
    # input port
    port = input("Enter port (2022): ")
    # input username
    username = input("Enter username: ")
    # input password
    password = input("Enter password: ")

    ssh_session(hostname, port, username, password)

if __name__ == '__main__':
    main()

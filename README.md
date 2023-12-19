## Terminal GPT agent
An autonomous GPT agent can take commands from a user and execute them on the remote machine by ssh.  
![image](assets/terminal_agent.png)  
Multiple subsequent ssh calls from the agent are available without interaction with the user.
### Requirements
* Linux
* OpenAI api key
### Install sshd
```
sudo apt install openssh-server
sudo systemctl start sshd
```
### Test sshd
```
ssh localhost -p 2022
```
### Install repo
```
git clone https://github.com/format37/terminal.git
cd terminal
python3 -m pip install -r requirements.txt
```
### Test repo
```
python3 ssh.py
```
## Caution!
Your agent knows your login and password and can hurt your system!  
### Run agent
Configure your agent in config.json  
Then run:
```
python3 agent.py
```
### Sample
[![IMAGE ALT TEXT HERE](assets/youtube_0.png)](https://youtu.be/n8_WRD7Ulg8?si=lAINq1mJ3ClhK4Vh)
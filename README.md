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
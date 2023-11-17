### Install sshd
```
sudo apt install openssh-server
sudo systemctl start sshd
```
### Test sshd
```
ssh localhost 2022
```
### Install repo
```
git clone https://github.com/format37/terminal.git
cd terminal
```
### Test repo
```
python3 ssh.py
```
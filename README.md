# 🐍 PyHTTP – Simple Authenticated Python File Server

`PyHTTP` is a lightweight Python HTTP file server with **Basic Authentication**.  
It lets you quickly share files from any directory over HTTP while protecting access with a username and password.

---

## 🚀 Features

- ⚡ One-line setup – no dependencies  
- 🔐 Basic authentication (username/password)  
- 📂 Serves files from the current directory  
- 🧰 Works anywhere Python 3 is available  

---

## 💻 Quick Start

Run this one-liner to **download**, **customize credentials**, and **start the server** instantly:

```bash
USER="user"; PASS="pass"; curl -sL https://raw.githubusercontent.com/vishvendrasingh/pyhttp/refs/heads/main/index.py | sed "s/basic_user/$USER/g; s/basic_pass/$PASS/g" > server.py && python3 server.py
````

📝 Replace `user` and `pass` with your desired username and password.

---

## 🧪 Example

```bash
USER="admin"; PASS="1234"; curl -sL https://raw.githubusercontent.com/vishvendrasingh/pyhttp/refs/heads/main/index.py | sed "s/basic_user/$USER/g; s/basic_pass/$PASS/g" > server.py && python3 server.py
```

Then open your browser and visit:

```
http://<your-ip>:8000
```

You’ll be prompted to enter your username and password.

---

## 🛠️ Requirements

* Python 3.x
* `curl` and `sed` (available on most Linux/Mac systems)

---

## 🧾 License

MIT License © 2025 [Vishvendra Singh]

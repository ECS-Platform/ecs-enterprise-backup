
#!/bin/bash
pkill -f uvicorn
pip install fastapi uvicorn jinja2 python-multipart
uvicorn app.main:app --reload &
sleep 5
open http://127.0.0.1:8000

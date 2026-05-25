# README

## env vars
```bash
touch .env
cat > .env << EOF
SCAN_DIR={PATH-TO-MUSICD-DIR}
DEST_TAR_PATH=./data.tar
DEST_DATA_PATH={PATH-TO-STORE-JSON-FILE}.json
EOF
```

## Run
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Personal notes
### Freeze dep
```bash
pip freeze > requirements.txt
```

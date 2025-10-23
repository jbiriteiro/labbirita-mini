# LabBirita Mini — Loja de Teste (Front + API Fake)

## Rodar localmente
1. Crie e ative venv:
   - `python -m venv venv`
   - Windows: `venv\Scripts\activate`
   - mac/linux: `source venv/bin/activate`

2. Instale dependências:
   - `pip install -r requirements.txt`

3. Rode:
   - `python app.py`
   - Acesse http://127.0.0.1:5000

OU (modo produção local):
   - `gunicorn app:app --bind 0.0.0.0:5000`

## Deploy no Render
1. Crie um repositório no GitHub e envie todos os arquivos.
2. Acesse https://render.com e crie conta (recomendo login via GitHub).
3. Clique **New +** → **Web Service**.
4. Conecte seu repo e selecione a branch (ex: main).
5. Build command: (deixe em branco) ou `pip install -r requirements.txt`
6. Start command: `gunicorn app:app --bind 0.0.0.0:$PORT`
7. Deploy — pronto. O serviço gratuito ativa no primeiro acesso.

**Obs:** Render fornece um domínio `*.onrender.com`. Use esse domínio pra testar anúncios, Pixel, etc.

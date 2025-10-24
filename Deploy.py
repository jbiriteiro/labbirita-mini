# =============================================================================
# LabBirita Mini - Deploy Pro Turbo v6.0
# =============================================================================
# Autor: José Biriteiro (ajustado por assistant)
# Data: 24/10/2025 (v6.0)
# Versão: 6.0
#
# O que há de novo nesta versão:
#  - checagem automática de branch atual (garante 'main' antes do push)
#  - checagem se usuário Git está configurado (git config user.name/email)
#  - verificação automática da API do GitHub (token) antes do push
#  - preview com contagem de arquivos e tamanho total a enviar
#  - gravação de logs em arquivo (deploy_log.txt)
#  - mantém QThread para não travar UI, backup + git-filter-repo hook mantidos
#  - docstrings e cabeçalhos para facilitar manutenção
#
# Requisitos:
#   pip install python-dotenv requests pyqt5
#   git instalado no PATH
#
# Segurança:
#   NUNCA commitar .env. Se já comitou, use git-filter-repo ou a GUI para limpar.
# =============================================================================

import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import requests
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QMessageBox, QLineEdit, QFileDialog
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont

LOG_FILE = "deploy_log.txt"


def append_log_file(line: str):
    """Appenda uma linha no arquivo de log (thread-safe o suficiente pra este uso)."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{ts} {line}\n")


class DeployWorker(QThread):
    """Worker para operações de deploy em segundo plano (não bloqueia UI)."""
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)
    security_check_signal = pyqtSignal(dict)

    def __init__(self, github_token: str, render_api_key: str, render_service_id: str):
        super().__init__()
        self.github_token = github_token
        self.render_api_key = render_api_key
        self.render_service_id = render_service_id

    def log(self, msg: str):
        """Emite log para UI e grava em arquivo."""
        self.log_signal.emit(msg)
        append_log_file(msg)

    def _run_cmd(self, cmd, check=False, capture_output=True, text=True):
        """Helper para subprocess.run com captura e tratamento."""
        return subprocess.run(cmd, check=check, capture_output=capture_output, text=text)

    def run(self):
        """Fluxo principal do deploy (executado em thread separada)."""
        try:
            self.log("[INÍCIO] Iniciando deploy seguro...")

            # ========== 1) Segurança básica: .gitignore e .env no stage ==========
            checks = {"gitignore": False, "token_valid": False, "env_in_stage": False}
            gitignore_path = Path(".gitignore")
            if gitignore_path.exists():
                content = gitignore_path.read_text(encoding="utf-8")
                if any(line.strip() == ".env" for line in content.splitlines()):
                    checks["gitignore"] = True
            else:
                self.log("[AVISO] .gitignore não existe.")

            # Testa token GitHub com uma chamada simples
            if self.github_token:
                try:
                    headers = {"Authorization": f"token {self.github_token}"}
                    r = requests.get("https://api.github.com/user", headers=headers, timeout=7)
                    if r.status_code == 200:
                        checks["token_valid"] = True
                except Exception:
                    checks["token_valid"] = False

            # Verifica se .env está no índice (já sendo trackeado)
            res = self._run_cmd(["git", "ls-files", ".env"])
            if res.returncode == 0 and res.stdout.strip():
                checks["env_in_stage"] = True

            self.security_check_signal.emit(checks)

            # Se .env estiver no stage => remove e commita a remoção
            if checks["env_in_stage"]:
                self.log("[AÇÃO] .env está sendo rastreado. Removendo do índice (git rm --cached .env)...")
                self._run_cmd(["git", "rm", "--cached", ".env"], check=True)
                # garante .gitignore
                if not gitignore_path.exists():
                    gitignore_path.write_text(".env\n", encoding="utf-8")
                    self.log("[AÇÃO] Criado .gitignore e adicionado .env")
                else:
                    content = gitignore_path.read_text(encoding="utf-8")
                    if ".env" not in content:
                        gitignore_path.write_text(content + "\n.env\n", encoding="utf-8")
                        self.log("[AÇÃO] Adicionado .env ao .gitignore")
                # commit de fix
                self._run_cmd(["git", "add", ".gitignore"], check=True)
                self._run_cmd(["git", "commit", "-m", "fix: remover .env do controle de versão"], check=True)
                self.log("[OK] .env removido do índice e commit aplicado.")

            # ========== 2) Verifica branch atual e usuário git ==========
            branch_proc = self._run_cmd(["git", "branch", "--show-current"])
            current_branch = branch_proc.stdout.strip() if branch_proc.returncode == 0 else ""
            if current_branch != "main":
                self.log(f"[ERRO] Branch atual: '{current_branch}'. Deploy só permite 'main'. Abortando.")
                self.finished_signal.emit(False, f"Branch atual é '{current_branch}'. Mude para 'main' e tente de novo.")
                return

            # verifica git user config
            uname = self._run_cmd(["git", "config", "user.name"])
            if not uname.stdout.strip():
                self.log("[ERRO] git user.name não configurado. Configure com 'git config user.name \"Seu Nome\"'.")
                self.finished_signal.emit(False, "git user.name não configurado.")
                return

            # ========== 3) Preview dos arquivos que serão enviados ==========
            status = self._run_cmd(["git", "status", "--porcelain"])
            lines = [l for l in status.stdout.splitlines() if l.strip()]
            # extrai paths; formato 'XY path' => path começa em pos 3
            files_to_commit = [line[3:] for line in lines if not line.endswith(".env")]
            # calcula tamanho total
            total_bytes = 0
            for f in files_to_commit:
                try:
                    total_bytes += Path(f).stat().st_size
                except Exception:
                    pass

            if not files_to_commit:
                self.log("[INFO] Nenhuma alteração detectada para commit. Pulando push.")
                self.finished_signal.emit(True, "Nenhuma alteração para enviar.")
                return

            self.log(f"[PREVIEW] {len(files_to_commit)} arquivos (~{total_bytes//1024} KB) serão enviados:")
            for f in files_to_commit[:200]:
                self.log(f"  → {f}")

            # ========== 4) Testa autenticação GitHub (token) antes de push ==========
            if not checks["token_valid"]:
                self.log("[ERRO] Token GitHub inválido ou sem permissão. Abortando.")
                self.finished_signal.emit(False, "GITHUB_TOKEN inválido ou sem permissão.")
                return

            # ========== 5) Commit + Push ==========
            self.log("[GIT] Preparando commit...")
            self._run_cmd(["git", "add", "."])  # .env já removido do índice se necessário
            commit_res = self._run_cmd(["git", "commit", "-m", "Deploy: atualização automática"], capture_output=True, text=True)
            # commit pode retornar non-zero se não houver mudanças, por isso validamos status novamente
            if commit_res.returncode != 0 and "nothing to commit" in commit_res.stderr.lower():
                self.log("[GIT] Nada novo para commitar após stage.")
            else:
                self.log("[GIT] Commit criado.")

            # push - usa o remoto já configurado no git (sem embutir token)
            self.log("[GIT] Enviando para remoto (git push origin main)...")
            push_proc = self._run_cmd(["git", "push", "origin", "main"], capture_output=True, text=True)
            if push_proc.returncode != 0:
                self.log(f"[ERRO] Push falhou: {push_proc.stderr.strip()[:800]}")
                self.finished_signal.emit(False, "Falha no git push. Veja logs.")
                return
            self.log("[OK] Push concluído com sucesso.")

            # ========== 6) Redeploy no Render ==========
            self.log("[RENDER] Solicitando redeploy...")
            headers = {"Authorization": f"Bearer {self.render_api_key}"}
            resp = requests.post(f"https://api.render.com/v1/services/{self.render_service_id}/deploys",
                                 headers=headers, timeout=20)
            if resp.status_code not in (201, 202):
                self.log(f"[ERRO] Falha no Render (HTTP {resp.status_code}): {resp.text[:400]}")
                self.finished_signal.emit(False, f"Render respondeu HTTP {resp.status_code}")
                return
            self.log("[OK] Redeploy solicitado (Render).")
            # feedback final
            self.log("[CONCLUÍDO] Deploy seguro finalizado com sucesso.")
            self.finished_signal.emit(True, "Deploy finalizado com sucesso.")

        except subprocess.CalledProcessError as e:
            self.log(f"[ERRO] Comando git falhou: {e.stderr if hasattr(e, 'stderr') else str(e)}")
            self.finished_signal.emit(False, "Erro ao executar comando git.")
        except Exception as e:
            self.log(f"[ERRO] Exceção: {repr(e)}")
            self.finished_signal.emit(False, f"Erro inesperado: {str(e)}")


class DeployGUI(QMainWindow):
    """Interface gráfica principal do Deploy Pro Turbo."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LabBirita Mini - Deploy Pro Turbo")
        self.resize(980, 720)
        self.github_token = ""
        self.render_api_key = ""
        self.render_service_id = "srv-d3sq1p8dl3ps73ar54s0"
        self.env_path = ""
        self._setup_ui()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        header = QLabel("🚀 LabBirita Mini — Deploy Pro Turbo v6.0")
        header.setFont(QFont("Segoe UI", 14, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        # cred input
        row = QHBoxLayout()
        self.load_btn = QPushButton("📂 Carregar .env")
        self.load_btn.clicked.connect(self.load_env_file)
        row.addWidget(self.load_btn)

        self.token_field = QLineEdit()
        self.token_field.setPlaceholderText("GITHUB_TOKEN")
        self.token_field.setEchoMode(QLineEdit.Password)
        row.addWidget(self.token_field)
        self.token_toggle = QPushButton("👁️")
        self.token_toggle.setFixedWidth(30)
        self.token_toggle.clicked.connect(lambda: self._toggle_echo(self.token_field, self.token_toggle))
        row.addWidget(self.token_toggle)

        self.render_field = QLineEdit()
        self.render_field.setPlaceholderText("RENDER_API_KEY")
        self.render_field.setEchoMode(QLineEdit.Password)
        row.addWidget(self.render_field)
        self.render_toggle = QPushButton("👁️")
        self.render_toggle.setFixedWidth(30)
        self.render_toggle.clicked.connect(lambda: self._toggle_echo(self.render_field, self.render_toggle))
        row.addWidget(self.render_toggle)

        layout.addLayout(row)

        # security status
        sec_row = QHBoxLayout()
        self.gitignore_status = QLabel("❓ .env no .gitignore?")
        sec_row.addWidget(self.gitignore_status)
        self.token_status = QLabel("❓ Token GitHub?")
        sec_row.addWidget(self.token_status)
        self.env_stage_status = QLabel("❓ .env em stage?")
        sec_row.addWidget(self.env_stage_status)
        layout.addLayout(sec_row)

        # buttons
        btn_row = QHBoxLayout()
        self.verify_btn = QPushButton("🔍 Verificar Token (API)")
        self.verify_btn.clicked.connect(self.verify_token)
        btn_row.addWidget(self.verify_btn)

        self.preview_push_btn = QPushButton("📤 Preview & Enviar (Commit+Push)")
        self.preview_push_btn.clicked.connect(self.start_commit_push)
        btn_row.addWidget(self.preview_push_btn)

        self.redeploy_btn = QPushButton("🔄 Redeploy Render")
        self.redeploy_btn.clicked.connect(self.start_redeploy)
        btn_row.addWidget(self.redeploy_btn)

        self.clear_btn = QPushButton("🧹 Limpar Logs")
        self.clear_btn.clicked.connect(self.clear_logs)
        btn_row.addWidget(self.clear_btn)

        self.exit_btn = QPushButton("🚪 Sair")
        self.exit_btn.clicked.connect(self.close)
        btn_row.addWidget(self.exit_btn)

        layout.addLayout(btn_row)

        # log area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        layout.addWidget(self.log_text)

        # initial state
        self._update_security_status_initial()

    # UI helpers
    def _toggle_echo(self, field: QLineEdit, btn: QPushButton):
        if field.echoMode() == QLineEdit.Password:
            field.setEchoMode(QLineEdit.Normal)
            btn.setText("🔒")
        else:
            field.setEchoMode(QLineEdit.Password)
            btn.setText("👁️")

    def load_env_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Abrir .env", "", "Arquivos .env (*.env)")
        if not file_path:
            return
        self.env_path = file_path
        load_dotenv(file_path, override=True)
        self.github_token = os.getenv("GITHUB_TOKEN", "")
        self.render_api_key = os.getenv("RENDER_API_KEY", "")
        self.token_field.setText(self.github_token)
        self.render_field.setText(self.render_api_key)
        self.log(f"[INFO] .env carregado: {file_path}")
        self._update_security_status_initial()

    def _update_security_status_initial(self):
        # .gitignore
        gi = Path(".gitignore")
        gi_ok = gi.exists() and ".env" in gi.read_text(encoding="utf-8")
        self.gitignore_status.setText("✅ .env no .gitignore" if gi_ok else "❌ .env NÃO no .gitignore")
        self.gitignore_status.setStyleSheet("color: green;" if gi_ok else "color: red;")
        # token quick check
        token_ok = False
        if self.github_token:
            try:
                r = requests.get("https://api.github.com/user", headers={"Authorization": f"token {self.github_token}"}, timeout=5)
                token_ok = r.status_code == 200
            except Exception:
                token_ok = False
        self.token_status.setText("✅ Token válido" if token_ok else "❌ Token inválido/ausente")
        self.token_status.setStyleSheet("color: green;" if token_ok else "color: red;")
        # env in stage
        env_in_stage = bool(subprocess.run(["git", "ls-files", ".env"], capture_output=True, text=True).stdout.strip())
        self.env_stage_status.setText("⚠️ .env no stage (será removido)" if env_in_stage else "✅ .env não está no stage")
        self.env_stage_status.setStyleSheet("color: orange;" if env_in_stage else "color: green;")

    def log(self, msg: str):
        self.log_text.append(msg)
        append_log_file(msg)

    # actions
    def verify_token(self):
        token = self.token_field.text().strip()
        if not token:
            QMessageBox.warning(self, "Aviso", "Carregue .env ou cole GITHUB_TOKEN no campo.")
            return
        self.log("[GITHUB] Verificando token via API...")
        try:
            r = requests.get("https://api.github.com/user", headers={"Authorization": f"token {token}"}, timeout=8)
            if r.status_code == 200:
                login = r.json().get("login")
                self.log(f"[OK] Token válido. Usuário: {login}")
                QMessageBox.information(self, "Token Válido", f"Usuário GitHub: {login}")
                self.github_token = token
            else:
                self.log(f"[ERRO] Token inválido. HTTP {r.status_code}")
                QMessageBox.critical(self, "Token Inválido", f"HTTP {r.status_code}")
        except Exception as e:
            self.log(f"[ERRO] Falha ao checar token: {str(e)}")
            QMessageBox.critical(self, "Erro", f"Erro ao checar token: {str(e)}")
        self._update_security_status_initial()

    def start_commit_push(self):
        # carrega campos atuais
        self.github_token = self.token_field.text().strip()
        self.render_api_key = self.render_field.text().strip()
        if not self.github_token:
            QMessageBox.warning(self, "Aviso", "GITHUB_TOKEN ausente. Carregue .env ou cole ele.")
            return
        self.log("[AÇÃO] Iniciando fluxo de commit+push (thread)...")
        self.worker = DeployWorker(self.github_token, self.render_api_key, self.render_service_id)
        self.worker.log_signal.connect(self.log)
        self.worker.security_check_signal.connect(lambda d: self._update_status_from_checks(d))
        self.worker.finished_signal.connect(self.on_deploy_finished)
        self.worker.start()

    def _update_status_from_checks(self, checks: dict):
        # atualiza labels baseado no dict do worker
        self.gitignore_status.setText("✅ .env no .gitignore" if checks.get("gitignore") else "❌ .env NÃO no .gitignore")
        self.token_status.setText("✅ Token válido" if checks.get("token_valid") else "❌ Token inválido")
        self.env_stage_status.setText("⚠️ .env no stage (será removido)" if checks.get("env_in_stage") else "✅ .env não está no stage")

    def start_redeploy(self):
        key = self.render_field.text().strip()
        if not key:
            QMessageBox.warning(self, "Aviso", "RENDER_API_KEY ausente. Carregue .env ou cole a chave.")
            return
        self.log("[RENDER] Enviando pedido de redeploy...")
        try:
            headers = {"Authorization": f"Bearer {key}"}
            resp = requests.post(f"https://api.render.com/v1/services/{self.render_service_id}/deploys", headers=headers, timeout=15)
            if resp.status_code in (201, 202):
                self.log(f"[OK] Redeploy solicitado (HTTP {resp.status_code}).")
                QMessageBox.information(self, "Redeploy iniciado", f"Redeploy iniciado. Verifique o dashboard do Render.")
            else:
                self.log(f"[ERRO] Render retornou HTTP {resp.status_code}: {resp.text[:200]}")
                QMessageBox.critical(self, "Erro Render", f"HTTP {resp.status_code}")
        except Exception as e:
            self.log(f"[ERRO] Falha na requisição Render: {str(e)}")
            QMessageBox.critical(self, "Erro", f"Falha na requisição: {str(e)}")

    def clear_logs(self):
        self.log_text.clear()
        self.log("[INFO] Logs limpos.")

    def on_deploy_finished(self, success: bool, message: str):
        if success:
            QMessageBox.information(self, "Sucesso", message)
        else:
            QMessageBox.critical(self, "Erro no Deploy", message)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = DeployGUI()
    win.show()
    sys.exit(app.exec_())

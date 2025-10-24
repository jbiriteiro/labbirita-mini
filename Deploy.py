# deploy_gui.py
import sys
import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv
import requests
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QMessageBox
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont


class DeployWorker(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, github_token, render_api_key, render_service_id):
        super().__init__()
        self.github_token = github_token
        self.render_api_key = render_api_key
        self.render_service_id = render_service_id

    def log(self, msg):
        self.log_signal.emit(msg)

    def run(self):
        try:
            self.log("[INÍCIO] Iniciando deploy seguro...\n")

            # --- 1. Garantir .gitignore ---
            gitignore_path = Path(".gitignore")
            if not gitignore_path.exists():
                gitignore_path.write_text(".env\nvenv/\n__pycache__/\n*.pyc\n")
                self.log("[OK] Arquivo .gitignore criado.")
            else:
                content = gitignore_path.read_text()
                if ".env" not in [line.strip() for line in content.splitlines()]:
                    with open(gitignore_path, "a") as f:
                        f.write("\n.env\n")
                    self.log("[OK] .env adicionado ao .gitignore.")

            # --- 2. Remover .env do stage se estiver trackeado ---
            result = subprocess.run(["git", "ls-files", ".env"], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                self.log("[AVISO] .env estava sendo trackeado! Removendo do stage...")
                subprocess.run(["git", "rm", "--cached", ".env"], check=True)
                subprocess.run(["git", "add", ".gitignore"], check=True)
                subprocess.run(["git", "commit", "-m", "fix: remover .env do controle de versão"], check=True)

            # --- 3. Verificar se .env está no stage AGORA (antes do commit) ---
            status_result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
            status_lines = status_result.stdout.splitlines()
            if any(line.endswith(".env") for line in status_lines):
                self.finished_signal.emit(False, "PERIGO: .env está no stage! Abortando deploy.")
                return

            # --- 4. Commit e push (só se houver alterações) ---
            if not status_lines:
                self.log("[INFO] Nenhuma alteração detectada. Pulando commit.")
            else:
                subprocess.run(["git", "add", "."], check=True)
                subprocess.run(["git", "commit", "-m", "Deploy: atualizacao automatica"], check=True)
                self.log("[GIT] Enviando para GitHub...")
                push_result = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True)
                if push_result.returncode != 0:
                    self.finished_signal.emit(False, f"Push falhou:\n{push_result.stderr}")
                    return
                self.log("[OK] Push concluído com sucesso!")

            # --- 5. Redeploy no Render ---
            self.log("[RENDER] Acionando redeploy...")
            headers = {"Authorization": f"Bearer {self.render_api_key}"}
            resp = requests.post(
                f"https://api.render.com/v1/services/{self.render_service_id}/deploys",
                headers=headers,
                timeout=15
            )
            if resp.status_code != 201:
                self.finished_signal.emit(False, f"Falha no Render (HTTP {resp.status_code})")
                return
            self.log("[OK] Redeploy solicitado com sucesso!")
            self.log("\n[CONCLUÍDO] Deploy seguro finalizado!")
            self.finished_signal.emit(True, "Sucesso!")

        except subprocess.CalledProcessError as e:
            self.finished_signal.emit(False, f"Erro no Git: {e}")
        except requests.RequestException as e:
            self.finished_signal.emit(False, f"Erro na API do Render: {e}")
        except Exception as e:
            self.finished_signal.emit(False, f"Erro inesperado: {str(e)}")


class DeployGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LabBirita Mini - Deploy Seguro")
        self.resize(720, 520)
        self.setToolTip("LabBirita Mini – Deploy automático com proteção contra vazamento de segredos")

        # Carregar variáveis de ambiente
        load_dotenv()
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.render_api_key = os.getenv("RENDER_API_KEY")
        self.render_service_id = "srv-d3sq1p8dl3ps73ar54s0"

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Status label
        self.status_label = QLabel("Verificando credenciais...")
        self.status_label.setFont(QFont("Segoe UI", 10))
        self.status_label.setToolTip(
            "Verifica se GITHUB_TOKEN e RENDER_API_KEY estão definidos no arquivo .env na raiz do projeto."
        )
        layout.addWidget(self.status_label)

        # Caixa de logs
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setToolTip(
            "Exibe logs em tempo real das operações:\n"
            "• Verificação de segurança\n"
            "• Comandos Git\n"
            "• Chamadas à API do GitHub e Render"
        )
        layout.addWidget(self.log_text)

        # Botão de deploy
        button_layout = QHBoxLayout()
        self.deploy_btn = QPushButton("🚀 Iniciar Deploy Seguro")
        self.deploy_btn.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.deploy_btn.setToolTip(
            "Executa o fluxo completo de deploy:\n"
            "1. Garante que .env não vá para o Git\n"
            "2. Faz commit das alterações\n"
            "3. Envia para o GitHub\n"
            "4. Aciona redeploy no Render\n\n"
            "⚠️ Requer arquivo .env com tokens válidos!"
        )
        self.deploy_btn.clicked.connect(self.start_deploy)
        button_layout.addWidget(self.deploy_btn)
        layout.addLayout(button_layout)

        self.update_status()

    def update_status(self):
        missing = []
        if not self.github_token:
            missing.append("GITHUB_TOKEN")
        if not self.render_api_key:
            missing.append("RENDER_API_KEY")

        if missing:
            self.status_label.setText(f"❌ Faltando no .env: {', '.join(missing)}")
            self.deploy_btn.setEnabled(False)
        else:
            self.status_label.setText("✅ Credenciais carregadas. Pronto para deploy.")
            self.deploy_btn.setEnabled(True)

    def log_message(self, msg):
        self.log_text.append(msg)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def start_deploy(self):
        self.deploy_btn.setEnabled(False)
        self.worker = DeployWorker(self.github_token, self.render_api_key, self.render_service_id)
        self.worker.log_signal.connect(self.log_message)
        self.worker.finished_signal.connect(self.on_deploy_finished)
        self.worker.start()

    def on_deploy_finished(self, success, message):
        self.deploy_btn.setEnabled(True)
        if not success:
            QMessageBox.critical(self, "Erro no Deploy", message)
            self.log_message(f"\n[ERRO] {message}")
        else:
            QMessageBox.information(self, "Sucesso!", "Deploy concluído com segurança!")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DeployGUI()
    window.show()
    sys.exit(app.exec_())
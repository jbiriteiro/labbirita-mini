# =============================================================================
# LabBirita Mini - Deploy Seguro com Interface Gráfica (PyQt5)
# =============================================================================
# Autor: José Biriteiro
# Projeto: https://github.com/jbiriteiro/labbirita-mini
# Data: 24 de outubro de 2025
# Versão: 5.4 (corrigida)
#
# Descrição:
# Aplicação GUI para deploy seguro do LabBirita Mini no GitHub + Render.
# Foco em: prevenção de vazamento de segredos, transparência e usabilidade.
#
# Funcionalidades:
#   📂 Carregar .env
#   👁️ Revelar/ocultar tokens
#   🔍 Verificar token do GitHub (log + msgbox)
#   📤 Deploy com preview de arquivos
#   🔄 Redeploy no Render
#   🧼 Limpar histórico com git-filter-repo + backup
#   🧹 Limpar tela
#   🚪 Finalizar com confirmação
#
# Requisitos:
#   pip install python-dotenv requests pyqt5 git-filter-repo
#
# Aviso:
#   - Nunca commitar .env
#   - Revogue tokens comprometidos imediatamente
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


class DeployWorker(QThread):
    """Worker para operações de deploy em segundo plano."""
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)
    security_check_signal = pyqtSignal(dict)

    def __init__(self, github_token: str, render_api_key: str, render_service_id: str):
        super().__init__()
        self.github_token = github_token
        self.render_api_key = render_api_key
        self.render_service_id = render_service_id

    def log(self, msg: str):
        self.log_signal.emit(msg)

    def run(self):
        try:
            self.log("[INÍCIO] Iniciando deploy seguro...\n")

            checks = {
                "gitignore": False,
                "token_valid": False,
                "env_in_stage": False
            }

            gitignore_path = Path(".gitignore")
            if gitignore_path.exists():
                content = gitignore_path.read_text()
                if ".env" in [line.strip() for line in content.splitlines()]:
                    checks["gitignore"] = True
            else:
                self.log("[AVISO] .gitignore não encontrado!")

            if self.github_token:
                try:
                    headers = {"Authorization": f"token {self.github_token}"}
                    user = requests.get("https://api.github.com/user", headers=headers, timeout=5).json()
                    checks["token_valid"] = True
                except:
                    pass

            result = subprocess.run(["git", "ls-files", ".env"], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                checks["env_in_stage"] = True

            self.security_check_signal.emit(checks)

            if checks["env_in_stage"]:
                self.log("[INFO] Removendo .env do stage...")
                subprocess.run(["git", "rm", "--cached", ".env"], check=True)
                subprocess.run(["git", "add", ".gitignore"], check=True)
                subprocess.run(["git", "commit", "-m", "fix: remover .env do controle de versão"], check=True)

            status_result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
            status_lines = [line for line in status_result.stdout.splitlines() if line.strip()]
            files_to_commit = [line[3:] for line in status_lines if not line.endswith(".env")]

            if not files_to_commit:
                self.log("[INFO] Nenhuma alteração detectada. Pulando commit.")
                self.log("[CONCLUÍDO] Deploy seguro finalizado!")
                self.finished_signal.emit(True, "Nenhuma alteração enviada.")
                return

            self.log("[PREVIEW] Arquivos que serão enviados:")
            for f in files_to_commit:
                self.log(f"  → {f}")

            subprocess.run(["git", "add", "."], check=True)
            subprocess.run(["git", "commit", "-m", "Deploy: atualizacao automatica"], check=True)
            self.log("\n[GIT] Enviando para GitHub...")
            push_result = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True)
            if push_result.returncode != 0:
                self.finished_signal.emit(False, f"Push falhou:\n{push_result.stderr}")
                return
            self.log("[OK] Push concluído com sucesso!")

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

        except Exception as e:
            self.finished_signal.emit(False, f"Erro: {str(e)}")


class DeployGUI(QMainWindow):
    """Interface gráfica principal do deploy seguro."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LabBirita Mini - Deploy Pro")
        self.resize(880, 700)
        self.setStyleSheet("background-color: #f9f9f9; font-family: 'Segoe UI';")

        self.github_token = ""
        self.render_api_key = ""
        self.render_service_id = "srv-d3sq1p8dl3ps73ar54s0"
        self.env_path = ""

        self._setup_ui()

    def _setup_ui(self):
        """Configura todos os widgets da interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        header_label = QLabel("🚀 LabBirita Mini - Deploy Pro")
        header_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        header_label.setAlignment(Qt.AlignCenter)
        header_label.setStyleSheet("color: #2c3e50; padding: 10px;")
        main_layout.addWidget(header_label)

        # === LINHA COMPLETA: Carregar .env + Tokens com olhinho ===
        cred_layout = QHBoxLayout()

        # Botão Carregar .env
        self.load_btn = QPushButton("📂 Carregar .env")
        self.load_btn.setToolTip("Selecione o arquivo .env com suas credenciais")
        self.load_btn.clicked.connect(self.load_env_file)
        cred_layout.addWidget(self.load_btn)

        # GITHUB_TOKEN com olhinho
        token_layout = QHBoxLayout()
        self.token_field = QLineEdit()
        self.token_field.setPlaceholderText("GITHUB_TOKEN")
        self.token_field.setEchoMode(QLineEdit.Password)
        token_layout.addWidget(self.token_field)

        self.toggle_token_btn = QPushButton("👁️")
        self.toggle_token_btn.setFixedWidth(30)
        self.toggle_token_btn.setToolTip("Mostrar/ocultar token")
        self.toggle_token_btn.clicked.connect(self.toggle_token_visibility)
        token_layout.addWidget(self.toggle_token_btn)
        cred_layout.addLayout(token_layout)

        # RENDER_API_KEY com olhinho
        render_layout = QHBoxLayout()
        self.render_field = QLineEdit()
        self.render_field.setPlaceholderText("RENDER_API_KEY")
        self.render_field.setEchoMode(QLineEdit.Password)
        render_layout.addWidget(self.render_field)

        self.toggle_render_btn = QPushButton("👁️")
        self.toggle_render_btn.setFixedWidth(30)
        self.toggle_render_btn.setToolTip("Mostrar/ocultar chave da API")
        self.toggle_render_btn.clicked.connect(self.toggle_render_visibility)
        render_layout.addWidget(self.toggle_render_btn)
        cred_layout.addLayout(render_layout)

        main_layout.addLayout(cred_layout)

        # Status de segurança
        sec_layout = QHBoxLayout()
        self.gitignore_status = QLabel("❓ .env no .gitignore?")
        self.gitignore_status.setStyleSheet("color: gray;")
        sec_layout.addWidget(self.gitignore_status)

        self.token_status = QLabel("❓ Token válido?")
        self.token_status.setStyleSheet("color: gray;")
        sec_layout.addWidget(self.token_status)

        self.env_stage_status = QLabel("❓ .env no stage?")
        self.env_stage_status.setStyleSheet("color: gray;")
        sec_layout.addWidget(self.env_stage_status)

        main_layout.addLayout(sec_layout)

        # Botões principais
        btn_layout = QHBoxLayout()
        self.verify_token_btn = QPushButton("🔍 Verificar Token GitHub")
        self.verify_token_btn.setToolTip("Testa se o GITHUB_TOKEN é válido e tem permissão de acesso")
        self.verify_token_btn.clicked.connect(self.verify_github_token)
        btn_layout.addWidget(self.verify_token_btn)

        self.commit_push_btn = QPushButton("📤 Enviar Atualizações")
        self.commit_push_btn.setToolTip("Mostra preview dos arquivos e envia para o GitHub")
        self.commit_push_btn.clicked.connect(self.start_commit_push)
        btn_layout.addWidget(self.commit_push_btn)

        self.redeploy_btn = QPushButton("🔄 Reiniciar Serviço no Render")
        self.redeploy_btn.setToolTip("Aciona redeploy no serviço Render")
        self.redeploy_btn.clicked.connect(self.start_redeploy)
        btn_layout.addWidget(self.redeploy_btn)

        self.clean_history_btn = QPushButton("🧼 Limpar Histórico")
        self.clean_history_btn.setToolTip(
            "Remove .env de TODO o histórico do Git (commits, branches, tags).\n"
            "Cria backup automático antes de limpar.\n"
            "Use SOMENTE se já commitou .env por acidente."
        )
        self.clean_history_btn.clicked.connect(self.backup_and_clean_history)
        btn_layout.addWidget(self.clean_history_btn)

        self.clear_logs_btn = QPushButton("🧹 Limpar Tela")
        self.clear_logs_btn.setToolTip("Limpa todos os logs anteriores")
        self.clear_logs_btn.clicked.connect(self.clear_logs)
        btn_layout.addWidget(self.clear_logs_btn)

        self.exit_btn = QPushButton("🚪 Finalizar")
        self.exit_btn.setToolTip("Fecha o aplicativo")
        self.exit_btn.clicked.connect(self.confirm_exit)
        btn_layout.addWidget(self.exit_btn)

        main_layout.addLayout(btn_layout)

        # Área de logs
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setStyleSheet("background-color: #ffffff; border: 1px solid #ddd;")
        main_layout.addWidget(self.log_text)

        self.update_buttons_state()

    # === FUNÇÕES PRINCIPAIS ===

    def load_env_file(self):
        """Carrega arquivo .env e atualiza campos com feedback visual."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Selecionar .env", "", "Arquivos .env (*.env)")
        if file_path:
            self.env_path = file_path
            load_dotenv(file_path, override=True)
            self.github_token = os.getenv("GITHUB_TOKEN", "")
            self.render_api_key = os.getenv("RENDER_API_KEY", "")
            self.token_field.setText("••••••••••••••••••••" if self.github_token else "")
            self.render_field.setText("••••••••••••••••••••" if self.render_api_key else "")
            self.update_buttons_state()
            self.log_message(f"[INFO] .env carregado de: {file_path}")
            QMessageBox.information(self, "✅ Arquivo Carregado", "Arquivo .env carregado com sucesso!")
        else:
            self.log_message("[INFO] Seleção de .env cancelada.")

    def update_buttons_state(self):
        has_token = bool(self.github_token)
        has_render_key = bool(self.render_api_key)
        self.verify_token_btn.setEnabled(has_token)
        self.commit_push_btn.setEnabled(has_token)
        self.redeploy_btn.setEnabled(has_render_key)
        self.clean_history_btn.setEnabled(True)

    def toggle_token_visibility(self):
        if self.token_field.echoMode() == QLineEdit.Password:
            self.token_field.setEchoMode(QLineEdit.Normal)
            self.toggle_token_btn.setText("🔒")
        else:
            self.token_field.setEchoMode(QLineEdit.Password)
            self.toggle_token_btn.setText("👁️")

    def toggle_render_visibility(self):
        if self.render_field.echoMode() == QLineEdit.Password:
            self.render_field.setEchoMode(QLineEdit.Normal)
            self.toggle_render_btn.setText("🔒")
        else:
            self.render_field.setEchoMode(QLineEdit.Password)
            self.toggle_render_btn.setText("👁️")

    def verify_github_token(self):
        token = self.github_token
        if not token:
            msg = "GITHUB_TOKEN não encontrado. Carregue um .env válido."
            self.log_message(f"[AVISO] {msg}")
            QMessageBox.warning(self, "Aviso", msg)
            return

        self.log_message("[GITHUB] Verificando token...")
        try:
            headers = {"Authorization": f"token {token}"}
            resp = requests.get("https://api.github.com/user", headers=headers, timeout=10)
            if resp.status_code == 200:
                user = resp.json()
                login = user.get("login", "desconhecido")
                success_msg = f"Token válido!\nUsuário: {login}"
                self.log_message(f"[OK] Token válido! Usuário: {login}")
                QMessageBox.information(self, "✅ Token Válido", success_msg)
            else:
                error_msg = f"Token inválido ou sem permissão.\nStatus HTTP: {resp.status_code}\nVerifique o escopo 'repo'."
                self.log_message(f"[ERRO] {error_msg.replace(chr(10), ' ')}")
                QMessageBox.critical(self, "❌ Token Inválido", error_msg)
        except Exception as e:
            msg = f"Erro ao verificar token: {str(e)}"
            self.log_message(f"[ERRO] {msg}")
            QMessageBox.critical(self, "Erro", msg)

    def backup_and_clean_history(self):
        try:
            if not os.path.exists(".git"):
                self.log_message("[ERRO] Pasta não é um repositório Git.")
                QMessageBox.warning(self, "Erro", "Esta pasta não é um repositório Git.")
                return

            try:
                subprocess.run(["git", "filter-repo", "--version"], check=True, capture_output=True)
            except FileNotFoundError:
                msg = "git-filter-repo não encontrado.\nInstale com: pip install git-filter-repo"
                self.log_message("[ERRO] " + msg.replace("\n", " "))
                QMessageBox.critical(self, "Ferramenta ausente", msg)
                return

            confirm = QMessageBox.question(
                self,
                "⚠️ Limpar Histórico Completo",
                "Esta ação:\n"
                "• Criará um backup automático\n"
                "• Removerá .env de TODOS os commits\n"
                "• Reescreverá o histórico local\n"
                "• Exigirá 'git push --force' depois\n\n"
                "⚠️ Só faça isso se já commitou .env por acidente.\n"
                "Deseja continuar?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if confirm != QMessageBox.Yes:
                self.log_message("[INFO] Operação cancelada.")
                return

            timestamp = datetime.now().strftime("%Y%m%d")
            backup_dir = f"labbirita-mini-backup-{timestamp}.git"
            self.log_message(f"[BACKUP] Criando backup em: {backup_dir}...")
            subprocess.run(["git", "clone", "--mirror", ".", backup_dir], check=True)
            self.log_message("[OK] Backup concluído!")

            self.log_message("\n[INFORMAÇÃO] Por que isso é necessário?")
            self.log_message("→ 'git rm --cached .env' só remove do stage atual.")
            self.log_message("→ O segredo continua nos commits anteriores.")
            self.log_message("→ O GitHub ainda detecta e bloqueia o push.")
            self.log_message("→ 'git-filter-repo' remove o arquivo de TODO o histórico.")
            self.log_message("→ É a única forma confiável de sanear o repositório.\n")

            self.log_message("[LIMPANDO] Removendo .env de todo o histórico...")
            result = subprocess.run(
                ["git", "filter-repo", "--path", ".env", "--invert-paths", "--force"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                self.log_message(f"[ERRO] Falha na limpeza: {result.stderr}")
                QMessageBox.critical(self, "Erro", "Falha ao limpar o histórico.")
                return

            self.log_message("[OK] Histórico limpo com sucesso!")
            self.log_message("[PRÓXIMO PASSO] Execute 'git push origin main --force'")
            QMessageBox.information(
                self,
                "✅ Histórico Sanitizado",
                f"Backup salvo em: {backup_dir}\n\n"
                "⚠️ Agora execute:\n"
                "   git push origin main --force"
            )

        except Exception as e:
            self.log_message(f"[ERRO] {str(e)}")
            QMessageBox.critical(self, "Erro", f"Erro: {str(e)}")

    def update_security_status(self, checks: dict):
        color_ok = "color: green;"
        color_bad = "color: red;"
        color_warn = "color: orange;"

        self.gitignore_status.setText("✅ .env no .gitignore" if checks.get("gitignore") else "❌ .env NÃO no .gitignore")
        self.gitignore_status.setStyleSheet(color_ok if checks.get("gitignore") else color_bad)

        self.token_status.setText("✅ Token válido" if checks.get("token_valid") else "❌ Token inválido")
        self.token_status.setStyleSheet(color_ok if checks.get("token_valid") else color_bad)

        self.env_stage_status.setText("⚠️ .env no stage (será removido)" if checks.get("env_in_stage") else "✅ .env não está no stage")
        self.env_stage_status.setStyleSheet(color_warn if checks.get("env_in_stage") else color_ok)

    def start_commit_push(self):
        if not self.github_token:
            QMessageBox.warning(self, "Aviso", "Carregue um .env com GITHUB_TOKEN válido.")
            return
        self.log_message("[INFO] Iniciando verificação de segurança...")
        self.worker = DeployWorker(self.github_token, self.render_api_key, self.render_service_id)
        self.worker.log_signal.connect(self.log_message)
        self.worker.security_check_signal.connect(self.update_security_status)
        self.worker.finished_signal.connect(self.on_deploy_finished)
        self.worker.start()

    def start_redeploy(self):
        if not self.render_api_key:
            QMessageBox.warning(self, "Aviso", "Carregue um .env com RENDER_API_KEY válido.")
            return
        self.log_message("[RENDER] Acionando redeploy...")
        try:
            headers = {"Authorization": f"Bearer {self.render_api_key}"}
            resp = requests.post(
                f"https://api.render.com/v1/services/{self.render_service_id}/deploys",
                headers=headers,
                timeout=15
            )
            if resp.status_code == 201:
                self.log_message("[OK] Redeploy solicitado com sucesso!")
                QMessageBox.information(self, "Sucesso!", "Redeploy acionado no Render!")
            else:
                self.log_message(f"[ERRO] Falha no Render: HTTP {resp.status_code}")
                QMessageBox.critical(self, "Erro", f"Falha no redeploy: {resp.status_code}")
        except Exception as e:
            self.log_message(f"[ERRO] Erro ao comunicar com Render: {str(e)}")
            QMessageBox.critical(self, "Erro", f"Erro de conexão: {str(e)}")

    def clear_logs(self):
        self.log_text.clear()
        self.log_message("[INFO] Logs limpos.")

    def confirm_exit(self):
        reply = QMessageBox.question(
            self, "Sair", "Tem certeza que deseja fechar o aplicativo?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.close()

    def log_message(self, msg: str):
        self.log_text.append(msg)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def on_deploy_finished(self, success: bool, message: str):
        if not success:
            QMessageBox.critical(self, "Erro no Deploy", message)
        else:
            QMessageBox.information(self, "Sucesso!", "Deploy concluído com segurança!")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DeployGUI()
    window.show()
    sys.exit(app.exec_())
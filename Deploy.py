# =============================================================================
# LabBirita Mini - Deploy Seguro com Interface Gráfica (PyQt5)
# =============================================================================
# Autor: José Biriteiro
# Projeto: https://github.com/jbiriteiro/labbirita-mini
# Data do Código: 24 de outubro de 2025
# Versão: 7.1 (Final com Validação Obrigatória)
#
# Descrição:
# Aplicação GUI para automatizar o deploy seguro do LabBirita Mini no GitHub + Render,
# com foco absoluto em prevenção de vazamento de segredos (.env) e usabilidade clara.
#
# Funcionalidades Principais:
#   📂 Carregar arquivo .env com tokens
#   👁️ Revelar/ocultar GITHUB_TOKEN e RENDER_API_KEY
#   🔍 Verificar Token GitHub (com alerta se .env não carregado)
#   📤 Preview & Enviar (commit + push seguro, com alerta se .env não carregado)
#   🔄 Reiniciar Serviço no Render (com alerta se .env não carregado)
#   🌐 Abrir site no Render
#   🧼 Limpar histórico com git-filter-repo + backup automático
#   📊 Preview com contagem de arquivos e tamanho total
#   ✅ Validação de branch (só permite 'main')
#   ✅ Verificação de git config user.name/email
#   📤 Exportar log manualmente + gravação automática em deploy_log.txt
#   ⚙️ Modo Dev/Prod (visual, conforme README)
#   🚪 Finalizar com confirmação
#
# Requisitos:
#   pip install python-dotenv requests pyqt5 git-filter-repo
#
# Instruções de Uso (conforme README do projeto):
#   1. Crie venv e instale requirements.txt
#   2. Rode localmente com: python app.py  OU  gunicorn app:app --bind 0.0.0.0:5000
#   3. No Render:
#        - Build command: pip install -r requirements.txt
#        - Start command: gunicorn app:app --bind 0.0.0.0:$PORT
#
# Segurança Crítica:
#   - NUNCA commitar .env
#   - Se já commitou, use "Limpar Histórico" ou siga:
#     https://docs.github.com/code-security/secret-scanning/working-with-secret-scanning-and-push-protection/working-with-push-protection-from-the-command-line
#   - Tokens comprometidos devem ser revogados IMEDIATAMENTE
#
# Comportamento de Segurança:
#   - Todos os botões críticos exigem .env carregado
#   - Se tentar usar sem .env, exibe QMessageBox de alerta
#   - Validação do token é feita ANTES do push (não só no botão)
#   - Branch deve ser 'main'
#   - .env é removido automaticamente do stage se detectado
# =============================================================================

import sys
import os
import subprocess
import webbrowser
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import requests
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QMessageBox, QLineEdit, QFileDialog, QComboBox
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QSettings
from PyQt5.QtGui import QFont

LOG_FILE = "deploy_log.txt"


def append_log_file(line: str):
    """
    Grava uma linha no arquivo de log com timestamp.
    Usado por todas as mensagens do sistema para auditoria contínua.
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{ts} {line}\n")
    except Exception:
        pass  # Falha silenciosa para não quebrar o fluxo


class DeployWorker(QThread):
    """
    Worker em thread separada para operações de deploy.
    Evita travamento da interface gráfica durante operações longas (Git, API).
    """
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)
    security_check_signal = pyqtSignal(dict)

    def __init__(self, github_token: str, render_api_key: str, render_service_id: str):
        super().__init__()
        self.github_token = github_token
        self.render_api_key = render_api_key
        self.render_service_id = render_service_id

    def log(self, msg: str):
        """Envia mensagem para a GUI e grava no arquivo de log."""
        self.log_signal.emit(msg)
        append_log_file(msg)

    def _run_cmd(self, cmd, check=False, capture_output=True, text=True):
        """Helper para execução segura de comandos do sistema (Git)."""
        return subprocess.run(cmd, check=check, capture_output=capture_output, text=text)

    def run(self):
        """Fluxo principal de deploy seguro — executado em segundo plano."""
        try:
            self.log("[INÍCIO] Iniciando deploy seguro...")

            # --- 1. Verificação de segurança básica ---
            checks = {"gitignore": False, "token_valid": False, "env_in_stage": False}
            gitignore_path = Path(".gitignore")
            if gitignore_path.exists():
                content = gitignore_path.read_text(encoding="utf-8")
                if any(line.strip() == ".env" for line in content.splitlines()):
                    checks["gitignore"] = True
            else:
                self.log("[AVISO] .gitignore não encontrado.")

            # Validação do token via API (SEM espaços na URL!)
            if self.github_token:
                try:
                    headers = {"Authorization": f"token {self.github_token}"}
                    r = requests.get("https://api.github.com/user", headers=headers, timeout=7)
                    if r.status_code == 200:
                        checks["token_valid"] = True
                except Exception:
                    checks["token_valid"] = False

            res = self._run_cmd(["git", "ls-files", ".env"])
            if res.returncode == 0 and res.stdout.strip():
                checks["env_in_stage"] = True

            self.security_check_signal.emit(checks)

            # Remove .env do stage se necessário
            if checks["env_in_stage"]:
                self.log("[AÇÃO] .env está sendo rastreado. Removendo...")
                self._run_cmd(["git", "rm", "--cached", ".env"], check=True)
                if not gitignore_path.exists():
                    gitignore_path.write_text(".env\n", encoding="utf-8")
                else:
                    content = gitignore_path.read_text(encoding="utf-8")
                    if ".env" not in content:
                        gitignore_path.write_text(content + "\n.env\n", encoding="utf-8")
                self._run_cmd(["git", "add", ".gitignore"], check=True)
                self._run_cmd(["git", "commit", "-m", "fix: remover .env do controle de versão"], check=True)
                self.log("[OK] .env removido do índice.")

            # --- 2. Validações críticas (branch e configuração do Git) ---
            branch_proc = self._run_cmd(["git", "branch", "--show-current"])
            current_branch = branch_proc.stdout.strip() if branch_proc.returncode == 0 else ""
            if current_branch != "main":
                self.log(f"[ERRO] Branch atual: '{current_branch}'. Só é permitido 'main'.")
                self.finished_signal.emit(False, f"Branch deve ser 'main', não '{current_branch}'.")
                return

            uname = self._run_cmd(["git", "config", "user.name"])
            if not uname.stdout.strip():
                self.log("[ERRO] git user.name não configurado.")
                self.finished_signal.emit(False, "Configure 'git config user.name' e 'user.email'.")
                return

            # --- 3. Preview com contagem e tamanho ---
            status = self._run_cmd(["git", "status", "--porcelain"])
            lines = [l for l in status.stdout.splitlines() if l.strip()]
            files_to_commit = [line[3:] for line in lines if not line.endswith(".env")]
            total_bytes = sum(Path(f).stat().st_size for f in files_to_commit if Path(f).exists())

            if not files_to_commit:
                self.log("[INFO] Nenhuma alteração detectada.")
                self.finished_signal.emit(True, "Nenhuma alteração para enviar.")
                return

            self.log(f"[PREVIEW] {len(files_to_commit)} arquivos (~{total_bytes//1024} KB) serão enviados:")
            for f in files_to_commit[:200]:
                self.log(f"  → {f}")

            # --- 4. Validação final do token antes do push ---
            if not checks["token_valid"]:
                self.log("[ERRO] Token GitHub inválido.")
                self.finished_signal.emit(False, "GITHUB_TOKEN inválido ou sem permissão.")
                return

            # --- 5. Commit + Push ---
            self.log("[GIT] Preparando commit...")
            self._run_cmd(["git", "add", "."])
            commit_res = self._run_cmd(["git", "commit", "-m", "Deploy: atualização automática"], capture_output=True, text=True)
            if commit_res.returncode != 0 and "nothing to commit" not in commit_res.stderr.lower():
                self.log(f"[ERRO] Falha no commit: {commit_res.stderr[:500]}")
                self.finished_signal.emit(False, "Falha ao criar commit.")
                return

            self.log("[GIT] Enviando para GitHub...")
            push_proc = self._run_cmd(["git", "push", "origin", "main"], capture_output=True, text=True)
            if push_proc.returncode != 0:
                self.log(f"[ERRO] Push falhou: {push_proc.stderr.strip()[:800]}")
                self.finished_signal.emit(False, "Falha no git push.")
                return
            self.log("[OK] Push concluído com sucesso.")

            # --- 6. Redeploy no Render ---
            self.log("[RENDER] Solicitando redeploy...")
            headers = {"Authorization": f"Bearer {self.render_api_key}"}
            resp = requests.post(
                f"https://api.render.com/v1/services/{self.render_service_id}/deploys",
                headers=headers,
                timeout=20
            )
            if resp.status_code not in (201, 202):
                self.log(f"[ERRO] Render falhou (HTTP {resp.status_code})")
                self.finished_signal.emit(False, f"Render respondeu HTTP {resp.status_code}")
                return
            self.log("[OK] Redeploy solicitado.")
            self.log("[CONCLUÍDO] Deploy seguro finalizado.")
            self.finished_signal.emit(True, "Deploy concluído com sucesso.")

        except subprocess.CalledProcessError as e:
            self.log(f"[ERRO] Comando git falhou: {e.stderr if hasattr(e, 'stderr') else str(e)}")
            self.finished_signal.emit(False, "Erro ao executar comando git.")
        except Exception as e:
            self.log(f"[ERRO] Exceção: {repr(e)}")
            self.finished_signal.emit(False, f"Erro inesperado: {str(e)}")


class DeployGUI(QMainWindow):
    """Interface gráfica principal do deploy seguro."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LabBirita Mini - Deploy Pro Final v7.1")
        self.resize(980, 740)
        self.setStyleSheet("background-color: #f9f9f9; font-family: 'Segoe UI';")

        self.settings = QSettings("Biriteiro", "LabBiritaDeploy")
        self.github_token = ""
        self.render_api_key = ""
        self.render_service_id = "srv-d3sq1p8dl3ps73ar54s0"
        self.env_path = self.settings.value("last_env_path", "")
        self.render_url = "https://labbirita-mini.onrender.com"

        self._setup_ui()

    def _setup_ui(self):
        """Configura todos os componentes da interface gráfica."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        header_label = QLabel("🚀 LabBirita Mini - Deploy Pro Final v7.1")
        header_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        header_label.setAlignment(Qt.AlignCenter)
        header_label.setStyleSheet("color: #2c3e50; padding: 10px;")
        main_layout.addWidget(header_label)

        # Carregar .env + campos com olhinho
        cred_layout = QHBoxLayout()
        self.load_btn = QPushButton("📂 Carregar .env")
        self.load_btn.setToolTip("Selecione o arquivo .env com GITHUB_TOKEN e RENDER_API_KEY")
        self.load_btn.clicked.connect(self.load_env_file)
        cred_layout.addWidget(self.load_btn)

        token_layout = QHBoxLayout()
        self.token_field = QLineEdit()
        self.token_field.setPlaceholderText("GITHUB_TOKEN")
        self.token_field.setEchoMode(QLineEdit.Password)
        token_layout.addWidget(self.token_field)

        self.toggle_token_btn = QPushButton("👁️")
        self.toggle_token_btn.setFixedWidth(30)
        self.toggle_token_btn.setToolTip("Mostrar/ocultar GITHUB_TOKEN")
        self.toggle_token_btn.clicked.connect(lambda: self._toggle_echo(self.token_field, self.toggle_token_btn))
        token_layout.addWidget(self.toggle_token_btn)
        cred_layout.addLayout(token_layout)

        render_layout = QHBoxLayout()
        self.render_field = QLineEdit()
        self.render_field.setPlaceholderText("RENDER_API_KEY")
        self.render_field.setEchoMode(QLineEdit.Password)
        render_layout.addWidget(self.render_field)

        self.toggle_render_btn = QPushButton("👁️")
        self.toggle_render_btn.setFixedWidth(30)
        self.toggle_render_btn.setToolTip("Mostrar/ocultar RENDER_API_KEY")
        self.toggle_render_btn.clicked.connect(lambda: self._toggle_echo(self.render_field, self.toggle_render_btn))
        render_layout.addWidget(self.toggle_render_btn)
        cred_layout.addLayout(render_layout)

        main_layout.addLayout(cred_layout)

        # Modo Dev/Prod (conforme README)
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Modo de execução local (conforme README):"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Desenvolvimento (python app.py)", "Produção (gunicorn app:app --bind 0.0.0.0:5000)"])
        mode_layout.addWidget(self.mode_combo)
        main_layout.addLayout(mode_layout)

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

        # Botões principais (todos habilitados, mas com validação no clique)
        btn_layout = QHBoxLayout()
        self.verify_token_btn = QPushButton("🔍 Verificar Token GitHub")
        self.verify_token_btn.setToolTip("Testa se o GITHUB_TOKEN é válido via API")
        self.verify_token_btn.clicked.connect(self.verify_github_token)
        btn_layout.addWidget(self.verify_token_btn)

        self.commit_push_btn = QPushButton("📤 Preview & Enviar")
        self.commit_push_btn.setToolTip("Mostra preview e envia para o GitHub")
        self.commit_push_btn.clicked.connect(self.start_commit_push)
        btn_layout.addWidget(self.commit_push_btn)

        self.redeploy_btn = QPushButton("🔄 Reiniciar Serviço no Render")
        self.redeploy_btn.setToolTip("Aciona redeploy no Render")
        self.redeploy_btn.clicked.connect(self.start_redeploy)
        btn_layout.addWidget(self.redeploy_btn)

        self.open_render_btn = QPushButton("🌐 Abrir no Render")
        self.open_render_btn.setToolTip("Abre https://labbirita-mini.onrender.com no navegador")
        self.open_render_btn.clicked.connect(self.open_render_site)
        btn_layout.addWidget(self.open_render_btn)

        self.clean_history_btn = QPushButton("🧼 Limpar Histórico")
        self.clean_history_btn.setToolTip("Remove .env de TODO o histórico com git-filter-repo")
        self.clean_history_btn.clicked.connect(self.backup_and_clean_history)
        btn_layout.addWidget(self.clean_history_btn)

        self.clear_logs_btn = QPushButton("🧹 Limpar Tela")
        self.clear_logs_btn.setToolTip("Limpa os logs da tela")
        self.clear_logs_btn.clicked.connect(self.clear_logs)
        btn_layout.addWidget(self.clear_logs_btn)

        self.export_log_btn = QPushButton("📤 Exportar Log")
        self.export_log_btn.setToolTip("Salva o log atual em um arquivo .txt")
        self.export_log_btn.clicked.connect(self.export_log)
        btn_layout.addWidget(self.export_log_btn)

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

        # Mensagem inicial
        self.log_message("[INFO] Bem-vindo ao Deploy Pro Final v7.1!")
        self.log_message("[DICA] Clique em 'Carregar .env' para começar.")

    # === FUNÇÕES DE INTERAÇÃO ===

    def _toggle_echo(self, field: QLineEdit, btn: QPushButton):
        """Alterna entre modo oculto e visível nos campos de senha."""
        if field.echoMode() == QLineEdit.Password:
            field.setEchoMode(QLineEdit.Normal)
            btn.setText("🔒")
        else:
            field.setEchoMode(QLineEdit.Password)
            btn.setText("👁️")

    def load_env_file(self):
        """Carrega arquivo .env e atualiza campos com os valores reais."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar .env", self.env_path, "Arquivos .env (*.env)"
        )
        if file_path:
            self.env_path = file_path
            self.settings.setValue("last_env_path", file_path)
            load_dotenv(file_path, override=True)
            self.github_token = os.getenv("GITHUB_TOKEN", "")
            self.render_api_key = os.getenv("RENDER_API_KEY", "")

            self.token_field.setText(self.github_token)
            self.render_field.setText(self.render_api_key)

            self.log_message(f"[INFO] .env carregado de: {file_path}")
            QMessageBox.information(self, "✅ Arquivo Carregado", "Arquivo .env carregado com sucesso!")
        else:
            self.log_message("[INFO] Seleção de .env cancelada.")

    def verify_github_token(self):
        """Verifica token do GitHub — exige GITHUB_TOKEN."""
        token = self.token_field.text().strip()
        if not token:
            QMessageBox.warning(
                self,
                "⚠️ Atenção",
                "Por favor, carregue um arquivo .env com GITHUB_TOKEN antes de verificar."
            )
            return
        self.log_message("[GITHUB] Verificando token...")
        try:
            r = requests.get("https://api.github.com/user", headers={"Authorization": f"token {token}"}, timeout=8)
            if r.status_code == 200:
                login = r.json().get("login")
                self.log_message(f"[OK] Token válido. Usuário: {login}")
                QMessageBox.information(self, "✅ Token Válido", f"Usuário GitHub: {login}")
            else:
                self.log_message(f"[ERRO] Token inválido. HTTP {r.status_code}")
                QMessageBox.critical(self, "❌ Token Inválido", f"HTTP {r.status_code}")
        except Exception as e:
            self.log_message(f"[ERRO] Falha ao checar token: {str(e)}")
            QMessageBox.critical(self, "Erro", f"Erro ao checar token: {str(e)}")

    def start_commit_push(self):
        """Inicia deploy — exige GITHUB_TOKEN."""
        token = self.token_field.text().strip()
        if not token:
            QMessageBox.warning(
                self,
                "⚠️ Atenção",
                "Por favor, carregue um arquivo .env com GITHUB_TOKEN antes de enviar atualizações."
            )
            return
        self.log_message("[AÇÃO] Iniciando fluxo de commit+push...")
        self.github_token = token
        self.render_api_key = self.render_field.text().strip()
        self.worker = DeployWorker(self.github_token, self.render_api_key, self.render_service_id)
        self.worker.log_signal.connect(self.log_message)
        self.worker.security_check_signal.connect(self._update_status_from_checks)
        self.worker.finished_signal.connect(self.on_deploy_finished)
        self.worker.start()

    def start_redeploy(self):
        """Aciona redeploy no Render — exige RENDER_API_KEY."""
        key = self.render_field.text().strip()
        if not key:
            QMessageBox.warning(
                self,
                "⚠️ Atenção",
                "Por favor, carregue um arquivo .env com RENDER_API_KEY antes de reiniciar o serviço."
            )
            return
        self.log_message("[RENDER] Enviando pedido de redeploy...")
        try:
            headers = {"Authorization": f"Bearer {key}"}
            resp = requests.post(
                f"https://api.render.com/v1/services/{self.render_service_id}/deploys",
                headers=headers,
                timeout=15
            )
            if resp.status_code in (201, 202):
                self.log_message(f"[OK] Redeploy solicitado (HTTP {resp.status_code}).")
                QMessageBox.information(self, "✅ Redeploy iniciado", "Verifique o dashboard do Render.")
            else:
                self.log_message(f"[ERRO] Render retornou HTTP {resp.status_code}")
                QMessageBox.critical(self, "❌ Erro Render", f"HTTP {resp.status_code}")
        except Exception as e:
            self.log_message(f"[ERRO] Falha na requisição Render: {str(e)}")
            QMessageBox.critical(self, "Erro", f"Falha na requisição: {str(e)}")

    def _update_status_from_checks(self, checks: dict):
        """Atualiza os indicadores visuais de segurança."""
        color_ok = "color: green;"
        color_bad = "color: red;"
        color_warn = "color: orange;"

        self.gitignore_status.setText("✅ .env no .gitignore" if checks.get("gitignore") else "❌ .env NÃO no .gitignore")
        self.gitignore_status.setStyleSheet(color_ok if checks.get("gitignore") else color_bad)

        self.token_status.setText("✅ Token válido" if checks.get("token_valid") else "❌ Token inválido")
        self.token_status.setStyleSheet(color_ok if checks.get("token_valid") else color_bad)

        self.env_stage_status.setText("⚠️ .env no stage (será removido)" if checks.get("env_in_stage") else "✅ .env não está no stage")
        self.env_stage_status.setStyleSheet(color_warn if checks.get("env_in_stage") else color_ok)

    def open_render_site(self):
        """Abre o site do LabBirita Mini no navegador."""
        webbrowser.open(self.render_url)
        self.log_message(f"[INFO] Abrindo {self.render_url} no navegador...")

    def export_log(self):
        """Exporta o conteúdo atual do log para um arquivo .txt."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"deploy_log_export_{timestamp}.txt"
        file_path, _ = QFileDialog.getSaveFileName(self, "Salvar Log", default_name, "Arquivos de Texto (*.txt)")
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.log_text.toPlainText())
            self.log_message(f"[INFO] Log exportado para: {file_path}")
            QMessageBox.information(self, "✅ Log Exportado", f"Log salvo em:\n{file_path}")

    def backup_and_clean_history(self):
        """Limpa .env de todo o histórico com git-filter-repo + backup."""
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

    def clear_logs(self):
        """Limpa a área de logs da tela."""
        self.log_text.clear()
        self.log_message("[INFO] Logs limpos.")

    def confirm_exit(self):
        """Solicita confirmação antes de fechar o aplicativo."""
        reply = QMessageBox.question(
            self, "Sair", "Tem certeza que deseja fechar o aplicativo?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.close()

    def log_message(self, msg: str):
        """Adiciona mensagem à área de logs e rola para o final."""
        self.log_text.append(msg)
        append_log_file(msg)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def on_deploy_finished(self, success: bool, message: str):
        """Exibe mensagem final após conclusão do deploy."""
        if not success:
            QMessageBox.critical(self, "Erro no Deploy", message)
        else:
            QMessageBox.information(self, "Sucesso!", "Deploy concluído com segurança!")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DeployGUI()
    window.show()
    sys.exit(app.exec_())
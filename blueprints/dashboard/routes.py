import secrets
import string
from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from extensions import db
from models import Hospital, Profissional, Paciente, RecomendacaoReceita, ReceitaPaciente, Sintoma, Consulta, Notificacao

dashboard_bp = Blueprint("dashboard", __name__)

def login_requerido(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("profissional_id"):
            return redirect(url_for("dashboard.login"))
        return f(*args, **kwargs)
    return wrapper


def papeis_permitidos(*papeis):
    def decorador(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            prof = profissional_atual()
            if not prof or prof.papel not in papeis:
                return render_template(
                    "dashboard/erro.html", prof=prof,
                    mensagem="Você não tem permissão para acessar esta página."
                ), 403
            return f(*args, **kwargs)
        return wrapper
    return decorador


def profissional_atual():
    pid = session.get("profissional_id")
    return Profissional.query.get(pid) if pid else None


def _query_notificacoes(prof):
    return Notificacao.query.filter(
        (Notificacao.hospital_id.is_(None)) | (Notificacao.hospital_id == prof.hospital_id)
    )


@dashboard_bp.context_processor
def injetar_notificacoes():
    
    prof = profissional_atual()
    if not prof:
        return {}
    nao_lidas = _query_notificacoes(prof).filter_by(lida=False).count()
    return dict(notificacoes_nao_lidas=nao_lidas)


@dashboard_bp.route("/notificacoes")
@login_requerido
def notificacoes():
    
    prof = profissional_atual()
    lista = _query_notificacoes(prof).order_by(Notificacao.criado_em.desc()).all()
    _query_notificacoes(prof).filter_by(lida=False).update({"lida": True}, synchronize_session=False)
    db.session.commit()
    return render_template("dashboard/notificacoes.html", prof=prof, lista=lista)



@dashboard_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("dashboard/login.html")

    email = request.form.get("email", "").strip().lower()
    senha = request.form.get("senha", "")
    prof = Profissional.query.filter_by(email=email).first()

    if not prof or not prof.checar_senha(senha):
        return render_template("dashboard/login.html", erro="E-mail ou senha incorretos.")

    session["profissional_id"] = prof.id
    return redirect(url_for("dashboard.home"))


@dashboard_bp.route("/logout")
def logout():
    session.pop("profissional_id", None)
    return redirect(url_for("dashboard.login"))



@dashboard_bp.route("/")
@login_requerido
def home():
    prof = profissional_atual()
    total_pacientes = Paciente.query.count()
    total_recomendacoes = RecomendacaoReceita.query.filter_by(profissional_id=prof.id).count() \
        if prof.papel in ("medico", "enfermeiro") else RecomendacaoReceita.query.count()
    total_vinculos = ReceitaPaciente.query.count()
    consultas_hoje = Consulta.query.filter_by(hospital_id=prof.hospital_id).count()
    ultimos_sintomas = Sintoma.query.order_by(Sintoma.data_registro.desc()).limit(6).all()
    return render_template(
        "dashboard/home.html",
        prof=prof,
        total_pacientes=total_pacientes,
        total_recomendacoes=total_recomendacoes,
        total_vinculos=total_vinculos,
        consultas_hoje=consultas_hoje,
        ultimos_sintomas=ultimos_sintomas,
    )


@dashboard_bp.route("/pacientes")
@login_requerido
def pacientes():
    termo = request.args.get("q", "").strip()
    resultados = []
    if termo:
        resultados = Paciente.query.filter(
            (Paciente.referencia.ilike(f"%{termo}%")) |
            (Paciente.email.ilike(f"%{termo}%")) |
            (Paciente.nome.ilike(f"%{termo}%"))
        ).all()
    else:
        resultados = Paciente.query.order_by(Paciente.criado_em.desc()).limit(20).all()
    return render_template("dashboard/pacientes.html", prof=profissional_atual(),
                            resultados=resultados, termo=termo)


@dashboard_bp.route("/pacientes/<referencia>")
@login_requerido
def paciente_detalhe(referencia):
    paciente = Paciente.query.filter_by(referencia=referencia).first_or_404()
    return render_template("dashboard/paciente_detalhe.html", prof=profissional_atual(), paciente=paciente)


@dashboard_bp.route("/pacientes/<referencia>/resetar-senha", methods=["POST"])
@login_requerido
@papeis_permitidos("admin")
def resetar_senha_paciente(referencia):

    paciente = Paciente.query.filter_by(referencia=referencia).first_or_404()
    alfabeto = string.ascii_letters + string.digits
    nova_senha = "".join(secrets.choice(alfabeto) for _ in range(10))
    paciente.set_senha(nova_senha)
    db.session.commit()
    return render_template(
        "dashboard/paciente_detalhe.html", prof=profissional_atual(),
        paciente=paciente, nova_senha=nova_senha,
    )


@dashboard_bp.route("/pacientes/<referencia>/deletar", methods=["POST"])
@login_requerido
@papeis_permitidos("admin")
def deletar_paciente(referencia):
    paciente = Paciente.query.filter_by(referencia=referencia).first_or_404()
    nome = paciente.nome
    db.session.delete(paciente)
    db.session.commit()
    flash(f"Paciente {nome} removido com sucesso.", "sucesso")
    return redirect(url_for("dashboard.pacientes"))


@dashboard_bp.route("/recomendacoes")
@login_requerido
@papeis_permitidos("medico", "enfermeiro", "analista", "admin")
def recomendacoes():
    lista = RecomendacaoReceita.query.order_by(RecomendacaoReceita.criado_em.desc()).all()
    return render_template("dashboard/recomendacoes.html", prof=profissional_atual(), lista=lista)


@dashboard_bp.route("/recomendacoes/nova", methods=["GET", "POST"])
@login_requerido
@papeis_permitidos("medico", "enfermeiro")
def nova_recomendacao():
    
    prof = profissional_atual()

    if request.method == "GET":
        return render_template("dashboard/nova_recomendacao.html", prof=prof)

    dados = request.form
    rec = RecomendacaoReceita(
        profissional_id=prof.id,
        titulo=dados.get("titulo", "").strip(),
        tipo=dados.get("tipo") or "medida_geral",
        descricao=dados.get("descricao", "").strip(),
        posologia=dados.get("posologia", "").strip() or None,
        idade_min=int(dados["idade_min"]) if dados.get("idade_min") else None,
        idade_max=int(dados["idade_max"]) if dados.get("idade_max") else None,
        peso_min_kg=float(dados["peso_min_kg"]) if dados.get("peso_min_kg") else None,
        contraindicacoes_alergia=dados.get("contraindicacoes_alergia", "").strip() or None,
    )
    db.session.add(rec)
    db.session.commit()

    return redirect(url_for("dashboard.recomendacoes"))


@dashboard_bp.route("/equipe")
@login_requerido
@papeis_permitidos("admin")
def equipe():
    prof = profissional_atual()
    membros = Profissional.query.filter_by(hospital_id=prof.hospital_id).all()
    return render_template("dashboard/equipe.html", prof=prof, membros=membros)


@dashboard_bp.route("/equipe/novo", methods=["GET", "POST"])
@login_requerido
@papeis_permitidos("admin")
def novo_profissional():
    prof = profissional_atual()

    if request.method == "GET":
        return render_template("dashboard/novo_profissional.html", prof=prof)

    dados = request.form
    if Profissional.query.filter_by(email=dados.get("email", "").strip().lower()).first():
        return render_template("dashboard/novo_profissional.html", prof=prof,
                                erro="Já existe um profissional com este e-mail.")

    novo = Profissional(
        hospital_id=prof.hospital_id,
        nome=dados.get("nome", "").strip(),
        email=dados.get("email", "").strip().lower(),
        papel=dados.get("papel", "medico"),
        registro_profissional=dados.get("registro_profissional") or None,
    )
    novo.set_senha(dados.get("senha", ""))
    db.session.add(novo)
    db.session.commit()

    return redirect(url_for("dashboard.equipe"))


@dashboard_bp.route("/equipe/<int:profissional_id>/editar", methods=["GET", "POST"])
@login_requerido
@papeis_permitidos("admin")
def editar_profissional(profissional_id):

    prof = profissional_atual()
    membro = Profissional.query.filter_by(id=profissional_id, hospital_id=prof.hospital_id).first_or_404()

    if request.method == "GET":
        return render_template("dashboard/editar_profissional.html", prof=prof, membro=membro)

    dados = request.form
    novo_email = dados.get("email", "").strip().lower()
    if novo_email and novo_email != membro.email:
        if Profissional.query.filter(Profissional.email == novo_email, Profissional.id != membro.id).first():
            return render_template("dashboard/editar_profissional.html", prof=prof, membro=membro,
                                    erro="Já existe um profissional com este e-mail.")
        membro.email = novo_email

    membro.nome = dados.get("nome", membro.nome).strip() or membro.nome
    membro.papel = dados.get("papel", membro.papel)
    membro.registro_profissional = dados.get("registro_profissional") or None

    nova_senha = dados.get("nova_senha", "").strip()
    if nova_senha:
        if len(nova_senha) < 6:
            return render_template("dashboard/editar_profissional.html", prof=prof, membro=membro,
                                    erro="A nova senha deve ter pelo menos 6 caracteres.")
        membro.set_senha(nova_senha)

    db.session.commit()
    flash(f"Dados de {membro.nome} atualizados com sucesso.", "sucesso")
    return redirect(url_for("dashboard.equipe"))


@dashboard_bp.route("/equipe/<int:profissional_id>/remover", methods=["POST"])
@login_requerido
@papeis_permitidos("admin")
def remover_profissional(profissional_id):
    prof = profissional_atual()
    if profissional_id == prof.id:
        flash("Você não pode remover a sua própria conta por aqui.", "erro")
        return redirect(url_for("dashboard.equipe"))

    membro = Profissional.query.filter_by(id=profissional_id, hospital_id=prof.hospital_id).first_or_404()
    nome = membro.nome
    db.session.delete(membro)
    db.session.commit()
    flash(f"{nome} removido da equipe.", "sucesso")
    return redirect(url_for("dashboard.equipe"))


@dashboard_bp.route("/perfil", methods=["GET", "POST"])
@login_requerido
def perfil():
    
    prof = profissional_atual()

    if request.method == "POST":
        dados = request.form

        novo_email = dados.get("email", "").strip().lower()
        if novo_email and novo_email != prof.email:
            if Profissional.query.filter(Profissional.email == novo_email, Profissional.id != prof.id).first():
                return render_template("dashboard/perfil.html", prof=prof,
                                        erro="Já existe um profissional com este e-mail.")
            prof.email = novo_email

        prof.nome = dados.get("nome", prof.nome).strip() or prof.nome

        nova_senha = dados.get("nova_senha", "").strip()
        if nova_senha:
            senha_atual = dados.get("senha_atual", "")
            if not prof.checar_senha(senha_atual):
                return render_template("dashboard/perfil.html", prof=prof,
                                        erro="Senha atual incorreta. A senha não foi alterada.")
            if len(nova_senha) < 6:
                return render_template("dashboard/perfil.html", prof=prof,
                                        erro="A nova senha deve ter pelo menos 6 caracteres.")
            prof.set_senha(nova_senha)

        db.session.commit()
        return render_template("dashboard/perfil.html", prof=prof, salvo=True)

    return render_template("dashboard/perfil.html", prof=prof)


@dashboard_bp.route("/consultas")
@login_requerido
def consultas():
    prof = profissional_atual()
    lista = Consulta.query.filter_by(hospital_id=prof.hospital_id).order_by(Consulta.data_hora).all()
    return render_template("dashboard/consultas.html", prof=prof, lista=lista)

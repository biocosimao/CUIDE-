from functools import wraps
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from extensions import db
from models import Farmacia, Farmaceutico, PedidoFarmacia

farmacia_bp = Blueprint("farmacia", __name__)



def login_requerido(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("farmaceutico_id"):
            return redirect(url_for("farmacia.login"))
        return f(*args, **kwargs)
    return wrapper


def farmaceutico_atual():
    fid = session.get("farmaceutico_id")
    return Farmaceutico.query.get(fid) if fid else None


@farmacia_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("farmacia/login.html")

    email = request.form.get("email", "").strip().lower()
    senha = request.form.get("senha", "")
    farm = Farmaceutico.query.filter_by(email=email).first()

    if not farm or not farm.checar_senha(senha):
        return render_template("farmacia/login.html", erro="E-mail ou senha incorretos.")

    session["farmaceutico_id"] = farm.id
    return redirect(url_for("farmacia.pedidos"))


@farmacia_bp.route("/logout")
def logout():
    session.pop("farmaceutico_id", None)
    return redirect(url_for("farmacia.login"))



@farmacia_bp.route("/")
@login_requerido
def pedidos():
    farm = farmaceutico_atual()
    pendentes = PedidoFarmacia.query.filter_by(
        farmacia_id=farm.farmacia_id, status="pendente"
    ).order_by(PedidoFarmacia.criado_em.asc()).all()
    respondidos = PedidoFarmacia.query.filter(
        PedidoFarmacia.farmacia_id == farm.farmacia_id,
        PedidoFarmacia.status != "pendente",
    ).order_by(PedidoFarmacia.respondido_em.desc()).limit(20).all()
    return render_template(
        "farmacia/pedidos.html", farm=farm, pendentes=pendentes, respondidos=respondidos
    )


@farmacia_bp.route("/pedidos/<int:pedido_id>/responder", methods=["POST"])
@login_requerido
def responder_pedido(pedido_id):
    
    farm = farmaceutico_atual()
    pedido = PedidoFarmacia.query.filter_by(id=pedido_id, farmacia_id=farm.farmacia_id).first_or_404()

    acao = request.form.get("acao")
    if acao == "disponivel":
        preco = request.form.get("preco", "").strip()
        try:
            pedido.preco = float(preco.replace(",", "."))
        except (TypeError, ValueError):
            flash("Informe um preço válido para confirmar a disponibilidade.", "erro")
            return redirect(url_for("farmacia.pedidos"))
        pedido.status = "disponivel"
        pedido.observacao = request.form.get("observacao") or None
    else:
        pedido.status = "indisponivel"
        pedido.preco = None
        pedido.observacao = request.form.get("observacao") or "Medicação indisponível nesta farmácia."

    pedido.farmaceutico_id = farm.id
    pedido.respondido_em = datetime.utcnow()
    db.session.commit()
    flash("Resposta enviada ao paciente.", "sucesso")
    return redirect(url_for("farmacia.pedidos"))

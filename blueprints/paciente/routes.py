from functools import wraps
from datetime import datetime as dt, date as _date, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, Response

from extensions import db
from models import (
    Paciente, Alergia, HistoricoDoenca, Sintoma, DiarioRegistro,
    ReceitaPaciente, RecomendacaoReceita, Hospital, Consulta, Lembrete,
    Notificacao, Farmacia, PedidoFarmacia, gerar_link_online,
)
from regras import verificar_compatibilidade

paciente_bp = Blueprint("paciente", __name__)


def parse_data_digitada(texto):

    if not texto:
        return None
    texto = texto.strip()
    try:
        if "/" in texto:
            dia, mes, ano = texto.split("/")
            return _date(int(ano), int(mes), int(dia))
        return _date.fromisoformat(texto)
    except (ValueError, TypeError):
        return None

def login_requerido(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("paciente_id"):
            return redirect(url_for("paciente.login"))
        return f(*args, **kwargs)
    return wrapper


def paciente_atual():
    pid = session.get("paciente_id")
    return Paciente.query.get(pid) if pid else None



@paciente_bp.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "GET":
        return render_template("cadastro.html")

    dados = request.form
    email = dados.get("email", "").strip().lower()

    if not dados.get("nome") or not email or not dados.get("senha"):
        return render_template("cadastro.html", erro="Preencha nome, e-mail e senha.")

    if Paciente.query.filter_by(email=email).first():
        return render_template("cadastro.html", erro="Já existe uma conta com este e-mail.")

    data_nascimento = parse_data_digitada(dados.get("data_nascimento"))

    paciente = Paciente(
        nome=dados.get("nome", "").strip(),
        email=email,
        telefone=dados.get("telefone") or None,
        data_nascimento=data_nascimento,
        sexo=dados.get("sexo") or None,
    )
    paciente.set_senha(dados.get("senha", ""))
    db.session.add(paciente)
    db.session.commit()

    db.session.add(Notificacao(
        tipo="novo_paciente",
        paciente_id=paciente.id,
        titulo="Novo paciente cadastrado",
        mensagem=f"{paciente.nome} criou uma conta no Cuide+ (ref. {paciente.referencia}).",
    ))
    db.session.commit()

    session["paciente_id"] = paciente.id
    return redirect(url_for("paciente.entrada_page"))


@paciente_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    senha = request.form.get("senha", "")
    paciente = Paciente.query.filter_by(email=email).first()

    if not paciente or not paciente.checar_senha(senha):
        return render_template("login.html", erro="E-mail ou senha incorretos.")

    session["paciente_id"] = paciente.id
    return redirect(url_for("paciente.entrada_page"))


@paciente_bp.route("/logout")
def logout():
    session.pop("paciente_id", None)
    return redirect(url_for("paciente.login"))



@paciente_bp.route("/entrada")
@login_requerido
def entrada_page():
    return render_template("entrada.html")


@paciente_bp.route("/")
@login_requerido
def home():
    p = paciente_atual()
    from datetime import datetime as _dt
    proxima = next((c for c in p.consultas if c.data_hora >= _dt.utcnow() and c.status == "agendada"), None)
    return render_template(
        "index.html",
        paciente=p,
        ultimo_sintoma=p.sintomas[0] if p.sintomas else None,
        proximo_lembrete=next((l for l in p.lembretes if l.ativo), None),
        proxima_consulta=proxima,
    )


@paciente_bp.route("/Sintomas")
@login_requerido
def sintomas_page():
    return render_template("Sintomas.html", paciente=paciente_atual())


@paciente_bp.route("/receita")
@login_requerido
def receitas_page():
    farmacias = Farmacia.query.all()
    return render_template("receita.html", paciente=paciente_atual(), farmacias=farmacias)


@paciente_bp.route("/diario")
@login_requerido
def diario_page():
    return render_template("diario.html", paciente=paciente_atual())


@paciente_bp.route("/dicas")
@login_requerido
def dicas_page():
    return render_template("dicas.html", paciente=paciente_atual())


@paciente_bp.route("/consultas")
@login_requerido
def consultas_page():
    hospitais = Hospital.query.all()
    return render_template("consultas.html", paciente=paciente_atual(), hospitais=hospitais)


@paciente_bp.route("/perfil", methods=["GET", "POST"])
@login_requerido
def perfil_page():
    p = paciente_atual()

    if request.method == "POST":
        dados = request.form

        novo_email = dados.get("email", "").strip().lower()
        if novo_email and novo_email != p.email:
            if Paciente.query.filter(Paciente.email == novo_email, Paciente.id != p.id).first():
                return render_template("perfil.html", paciente=p, erro="Já existe uma conta com este e-mail.")
            p.email = novo_email

        p.nome = dados.get("nome", p.nome).strip() or p.nome
        p.telefone = dados.get("telefone") or p.telefone
        p.sexo = dados.get("sexo") or p.sexo

        if dados.get("data_nascimento"):
            nova_data = parse_data_digitada(dados["data_nascimento"])
            if nova_data:
                p.data_nascimento = nova_data

        p.peso_kg = float(dados["peso_kg"]) if dados.get("peso_kg") else p.peso_kg
        p.altura_cm = float(dados["altura_cm"]) if dados.get("altura_cm") else p.altura_cm
        p.tipo_sanguineo = dados.get("tipo_sanguineo") or p.tipo_sanguineo
        p.tabagismo = dados.get("tabagismo") or p.tabagismo
        p.consumo_alcool = dados.get("consumo_alcool") or p.consumo_alcool
        p.atividade_fisica = dados.get("atividade_fisica") or p.atividade_fisica
        p.qualidade_sono = dados.get("qualidade_sono") or p.qualidade_sono
        p.alimentacao_habitual = dados.get("alimentacao_habitual") or p.alimentacao_habitual

        # Alergias: substitui a lista pela informada agora
        novas_alergias = [a.strip() for a in dados.get("alergias", "").split(",") if a.strip()]
        Alergia.query.filter_by(paciente_id=p.id).delete()
        for a in novas_alergias:
            db.session.add(Alergia(paciente_id=p.id, tipo="geral", descricao=a))

        # Doenças e condições relevantes / doenças atuais em análise
        HistoricoDoenca.query.filter_by(paciente_id=p.id).delete()
        for d in [x.strip() for x in dados.get("condicoes_relevantes", "").split(",") if x.strip()]:
            db.session.add(HistoricoDoenca(paciente_id=p.id, doenca=d, tipo="cronica_ou_congenita"))
        for d in [x.strip() for x in dados.get("doencas_atuais", "").split(",") if x.strip()]:
            db.session.add(HistoricoDoenca(paciente_id=p.id, doenca=d, tipo="atual_em_analise"))

        db.session.add(Notificacao(
            tipo="atualizacao_paciente",
            paciente_id=p.id,
            titulo="Dados de paciente actualizados",
            mensagem=f"{p.nome} (ref. {p.referencia}) actualizou os seus dados no perfil.",
        ))
        db.session.commit()
        return render_template("perfil.html", paciente=p, salvo=True)

    return render_template("perfil.html", paciente=p)


@paciente_bp.route("/relatorio")
@login_requerido
def relatorio_page():
    periodo = request.args.get("periodo", "semanal")
    p = paciente_atual()

    faltando = []
    if not p.data_nascimento:
        faltando.append("Data de nascimento")
    if not p.sexo:
        faltando.append("Sexo")
    if not p.diario:
        faltando.append("Registros do diário (alimentação/hidratação)")

    return render_template("relatorio.html", paciente=p, periodo=periodo, faltando=faltando)


def _dados_relatorio(p, periodo):
    from datetime import timedelta
    dias = 7 if periodo == "semanal" else 30
    limite = dt.utcnow() - timedelta(days=dias)
    sintomas = [s for s in p.sintomas if s.data_registro >= limite]
    diario = [d for d in p.diario if dt.combine(d.data, dt.min.time()) >= limite]
    return sintomas, diario


@paciente_bp.route("/api/relatorio/gerar", methods=["POST"])
@login_requerido
def api_gerar_relatorio():
    
    p = paciente_atual()
    periodo = (request.get_json(silent=True) or {}).get("periodo", "semanal")
    sintomas, diario = _dados_relatorio(p, periodo)

    if not sintomas and not diario:
        resumo = "Não há registros suficientes neste período para compilar um relatório."
        return jsonify({"texto": resumo})

    partes = ["## Resumo"]
    if sintomas:
        nomes = ", ".join(sorted({s.descricao for s in sintomas}))
        partes.append(
            f"No período, foram registrados {len(sintomas)} sintoma(s): {nomes}."
        )
    else:
        partes.append("Nenhum sintoma foi registrado neste período.")

    if diario:
        media_agua = sum(d.agua_copos or 0 for d in diario) / len(diario)
        media_sono = sum(d.horas_sono or 0 for d in diario) / len(diario)
        partes.append(
            f"A média de hidratação foi de {media_agua:.1f} copos/dia e de sono, "
            f"{media_sono:.1f}h/dia, com base em {len(diario)} registro(s) do diário."
        )

    partes.append("\n## Possíveis padrões")
    if len(sintomas) >= 2:
        partes.append("Mais de um sintoma foi registrado no período — vale observar se ocorrem juntos ou em sequência.")
    elif len(sintomas) == 1:
        partes.append("Foi registrado um evento pontual, sem repetição no período.")
    else:
        partes.append("Sem sintomas no período, o que sugere estabilidade no quadro geral.")

    partes.append("\n## Sugestões (não prescritivas)")
    partes.append(
        "Continue registrando sintomas e hábitos diariamente para relatórios mais precisos. "
        "Se algum sintoma persistir ou piorar, procure avaliação médica presencial — "
        "este app não prescreve nem substitui uma consulta."
    )

    return jsonify({"texto": "\n".join(partes)})


@paciente_bp.route("/relatorio/exportar.<formato>")
@login_requerido
def exportar_relatorio(formato):
    p = paciente_atual()
    periodo = request.args.get("periodo", "semanal")
    sintomas, diario = _dados_relatorio(p, periodo)

    if formato == "csv":
        import csv
        import io
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["tipo", "descricao", "detalhe1", "detalhe2", "data"])
        for s in sintomas:
            writer.writerow(["sintoma", s.descricao, f"intensidade {s.intensidade}", s.observacoes or "", s.data_registro.strftime("%d/%m/%Y %H:%M")])
        for d in diario:
            writer.writerow(["diario", d.alimentacao or "", f"{d.agua_copos} copos", f"{d.horas_sono}h sono", d.data.strftime("%d/%m/%Y")])
        return Response(
            buf.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename=relatorio_{periodo}.csv"},
        )

    if formato == "pdf":
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "Cuide+ - Relatorio do paciente", ln=True)
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 8, f"Paciente: {p.nome} ({p.referencia})", ln=True)
        pdf.cell(0, 8, f"Periodo: {periodo}", ln=True)
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Sintomas", ln=True)
        pdf.set_font("Helvetica", "", 10)
        if sintomas:
            for s in sintomas:
                linha = f"- {s.descricao} (intensidade {s.intensidade}) em {s.data_registro.strftime('%d/%m/%Y %H:%M')}"
                pdf.multi_cell(0, 6, linha)
        else:
            pdf.cell(0, 6, "Nenhum sintoma registrado.", ln=True)
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Diario", ln=True)
        pdf.set_font("Helvetica", "", 10)
        if diario:
            for d in diario:
                linha = f"- {d.data.strftime('%d/%m/%Y')}: {d.agua_copos} copos de agua, {d.horas_sono}h de sono"
                pdf.multi_cell(0, 6, linha)
        else:
            pdf.cell(0, 6, "Nenhum registro no diario.", ln=True)

        pdf_bytes = bytes(pdf.output(dest="S"))
        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=relatorio_{periodo}.pdf"},
        )

    return jsonify({"erro": "Formato inválido."}), 400



@paciente_bp.route("/api/paciente")
@login_requerido
def api_paciente():
    return jsonify(paciente_atual().to_dict())


@paciente_bp.route("/api/sintomas", methods=["GET", "POST"])
@login_requerido
def api_sintomas():
    p = paciente_atual()

    if request.method == "POST":
        dados = request.get_json(silent=True) or {}
        descricao = (dados.get("descricao") or "").strip()
        if not descricao:
            return jsonify({"erro": "Descreva o sintoma."}), 400

        data_inicio = None
        if dados.get("data_inicio"):
            try:
                data_inicio = dt.fromisoformat(dados["data_inicio"])
            except ValueError:
                data_inicio = None

        sintoma = Sintoma(
            paciente_id=p.id,
            descricao=descricao,
            intensidade=int(dados.get("intensidade", 5)),
            observacoes=dados.get("observacoes") or None,
            data_inicio=data_inicio,
        )
        db.session.add(sintoma)
        db.session.commit()
        return jsonify(sintoma.to_dict()), 201

    return jsonify([s.to_dict() for s in p.sintomas])


@paciente_bp.route("/api/sintomas/<int:sintoma_id>", methods=["DELETE"])
@login_requerido
def api_deletar_sintoma(sintoma_id):
    p = paciente_atual()
    sintoma = Sintoma.query.filter_by(id=sintoma_id, paciente_id=p.id).first()
    if not sintoma:
        return jsonify({"erro": "Sintoma não encontrado."}), 404
    db.session.delete(sintoma)
    db.session.commit()
    return jsonify({"ok": True})


@paciente_bp.route("/api/recomendacoes-aplicaveis")
@login_requerido
def api_recomendacoes_aplicaveis():
    
    p = paciente_atual()
    todas = RecomendacaoReceita.query.order_by(RecomendacaoReceita.criado_em.desc()).limit(20).all()
    resultado = []
    for rec in todas:
        status, motivo = verificar_compatibilidade(p, rec)
        item = rec.to_dict()
        item["status"] = status
        item["motivo"] = motivo
        resultado.append(item)
    return jsonify(resultado)


@paciente_bp.route("/api/diario", methods=["GET", "POST"])
@login_requerido
def api_diario():
    p = paciente_atual()

    if request.method == "POST":
        dados = request.get_json(silent=True) or {}
        registro = DiarioRegistro(
            paciente_id=p.id,
            refeicao=dados.get("refeicao") or None,
            agua_copos=float(dados.get("agua_copos") or 0),
            horas_sono=float(dados.get("horas_sono") or 0),
            como_se_sentiu=dados.get("como_se_sentiu") or None,
            alimentacao=dados.get("alimentacao"),
        )
        db.session.add(registro)
        db.session.commit()
        return jsonify(registro.to_dict()), 201

    periodo = request.args.get("periodo", "hoje")
    query = DiarioRegistro.query.filter_by(paciente_id=p.id)
    if periodo == "semana":
        limite = _date.today() - timedelta(days=6)
        query = query.filter(DiarioRegistro.data >= limite)
    else:
        query = query.filter(DiarioRegistro.data == _date.today())
    registros = query.order_by(DiarioRegistro.data.desc(), DiarioRegistro.id.desc()).all()
    return jsonify([d.to_dict() for d in registros])


@paciente_bp.route("/api/receitas", methods=["GET"])
@login_requerido
def api_receitas():
    p = paciente_atual()
    return jsonify([r.to_dict() for r in p.receitas])


@paciente_bp.route("/api/receitas/vincular", methods=["POST"])
@login_requerido
def api_vincular_receita():
    
    p = paciente_atual()
    dados = request.get_json(silent=True) or {}
    codigo = (dados.get("codigo") or "").strip().upper()

    recomendacao = RecomendacaoReceita.query.filter_by(codigo=codigo).first()
    if not recomendacao:
        return jsonify({"erro": "Código não encontrado. Confirme com o hospital."}), 404

    ja_vinculada = ReceitaPaciente.query.filter_by(
        paciente_id=p.id, recomendacao_id=recomendacao.id
    ).first()
    if ja_vinculada:
        return jsonify({"erro": "Esta receita já está vinculada à sua conta."}), 400

    status, motivo = verificar_compatibilidade(p, recomendacao)

    vinculo = ReceitaPaciente(
        paciente_id=p.id,
        recomendacao_id=recomendacao.id,
        status=status,
        motivo=motivo,
    )
    db.session.add(vinculo)
    db.session.commit()

    return jsonify(vinculo.to_dict()), 201


@paciente_bp.route("/api/receitas/<int:receita_id>/iniciar", methods=["POST"])
@login_requerido
def api_iniciar_receita(receita_id):
    
    p = paciente_atual()
    vinculo = ReceitaPaciente.query.filter_by(id=receita_id, paciente_id=p.id).first()
    if not vinculo:
        return jsonify({"erro": "Receita não encontrada."}), 404
    if vinculo.status != "compativel":
        return jsonify({"erro": "Esta receita não é compatível com o seu histórico e não pode ser iniciada."}), 400

    vinculo.iniciada = True
    lembrete = Lembrete(
        paciente_id=p.id,
        receita_id=vinculo.id,
        titulo=f"Tomar: {vinculo.recomendacao.titulo}",
        hora=request.get_json(silent=True).get("hora", "08:00") if request.get_json(silent=True) else "08:00",
    )
    db.session.add(lembrete)
    db.session.commit()
    return jsonify({"vinculo": vinculo.to_dict(), "lembrete": lembrete.to_dict()}), 201


@paciente_bp.route("/api/receitas/<int:receita_id>/enviar-farmacia", methods=["POST"])
@login_requerido
def api_enviar_receita_farmacia(receita_id):
    
    p = paciente_atual()
    vinculo = ReceitaPaciente.query.filter_by(id=receita_id, paciente_id=p.id).first()
    if not vinculo:
        return jsonify({"erro": "Receita não encontrada."}), 404
    if vinculo.status != "compativel":
        return jsonify({"erro": "Só é possível enviar para a farmácia receitas compatíveis."}), 400

    dados = request.get_json(silent=True) or {}
    farmacia_id = dados.get("farmacia_id")
    farmacia = Farmacia.query.get(farmacia_id) if farmacia_id else None
    if not farmacia:
        return jsonify({"erro": "Escolha uma farmácia válida."}), 400

    ja_pendente = PedidoFarmacia.query.filter_by(
        receita_paciente_id=vinculo.id, farmacia_id=farmacia.id, status="pendente"
    ).first()
    if ja_pendente:
        return jsonify({"erro": "Já existe um pedido pendente para esta farmácia."}), 400

    pedido = PedidoFarmacia(receita_paciente_id=vinculo.id, farmacia_id=farmacia.id)
    db.session.add(pedido)
    db.session.commit()
    return jsonify(pedido.to_dict()), 201


@paciente_bp.route("/api/farmacias")
@login_requerido
def api_farmacias():
    return jsonify([{"id": f.id, "nome": f.nome, "endereco": f.endereco} for f in Farmacia.query.all()])


@paciente_bp.route("/api/consultas", methods=["GET", "POST"])
@login_requerido
def api_consultas():
    p = paciente_atual()

    if request.method == "POST":
        dados = request.get_json(silent=True) or {}
        hospital_id = dados.get("hospital_id")
        data_hora = dados.get("data_hora")
        if not hospital_id or not data_hora:
            return jsonify({"erro": "Escolha o hospital e a data/hora."}), 400

        tipo = dados.get("tipo") if dados.get("tipo") in ("online", "presencial") else "presencial"

        from datetime import datetime as dt
        consulta = Consulta(
            paciente_id=p.id,
            hospital_id=hospital_id,
            motivo=dados.get("motivo") or "Consulta geral",
            data_hora=dt.fromisoformat(data_hora),
            tipo=tipo,
            link_online=gerar_link_online() if tipo == "online" else None,
        )
        db.session.add(consulta)
        db.session.commit()

        hospital = Hospital.query.get(hospital_id)
        db.session.add(Notificacao(
            tipo="nova_consulta",
            hospital_id=hospital_id,
            paciente_id=p.id,
            titulo="Nova consulta marcada",
            mensagem=(
                f"{p.nome} marcou uma consulta {'online' if tipo == 'online' else 'presencial'} "
                f"em {hospital.nome if hospital else 'hospital'} para "
                f"{consulta.data_hora.strftime('%d/%m/%Y %H:%M')}."
            ),
        ))
        db.session.commit()

        return jsonify(consulta.to_dict()), 201

    return jsonify([c.to_dict() for c in p.consultas])


@paciente_bp.route("/api/lembretes")
@login_requerido
def api_lembretes():
    p = paciente_atual()
    return jsonify([l.to_dict() for l in p.lembretes])

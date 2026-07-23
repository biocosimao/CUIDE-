
from datetime import datetime, date
import random
import string

from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db


def gerar_referencia():
    return "CP-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


def gerar_codigo_receita():
    return "RX-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=4))


class Paciente(db.Model):
    __tablename__ = "pacientes"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    telefone = db.Column(db.String(30))
    senha_hash = db.Column(db.String(255), nullable=False)
    referencia = db.Column(db.String(20), unique=True, default=gerar_referencia)

    data_nascimento = db.Column(db.Date)
    sexo = db.Column(db.String(20))
    peso_kg = db.Column(db.Float)
    altura_cm = db.Column(db.Float)
    tipo_sanguineo = db.Column(db.String(5))

    tabagismo = db.Column(db.String(20))           
    consumo_alcool = db.Column(db.String(20))       
    atividade_fisica = db.Column(db.String(20))     
    qualidade_sono = db.Column(db.String(20))        
    alimentacao_habitual = db.Column(db.Text)

    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    alergias = db.relationship("Alergia", backref="paciente", cascade="all, delete-orphan")
    historico_doencas = db.relationship("HistoricoDoenca", backref="paciente", cascade="all, delete-orphan")
    sintomas = db.relationship("Sintoma", backref="paciente", cascade="all, delete-orphan",
                                order_by="Sintoma.data_registro.desc()")
    receitas = db.relationship("ReceitaPaciente", backref="paciente", cascade="all, delete-orphan",
                                order_by="ReceitaPaciente.vinculado_em.desc()")
    diario = db.relationship("DiarioRegistro", backref="paciente", cascade="all, delete-orphan",
                              order_by="DiarioRegistro.data.desc()")
    consultas = db.relationship("Consulta", backref="paciente", cascade="all, delete-orphan",
                                 order_by="Consulta.data_hora")
    lembretes = db.relationship("Lembrete", backref="paciente", cascade="all, delete-orphan",
                                 order_by="Lembrete.hora")

    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def checar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)

    @property
    def idade(self):
        if not self.data_nascimento:
            return None
        hoje = date.today()
        anos = hoje.year - self.data_nascimento.year
        if (hoje.month, hoje.day) < (self.data_nascimento.month, self.data_nascimento.day):
            anos -= 1
        return anos

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "email": self.email,
            "telefone": self.telefone,
            "referencia": self.referencia,
            "data_nascimento": self.data_nascimento.strftime("%Y-%m-%d") if self.data_nascimento else None,
            "idade": self.idade,
            "sexo": self.sexo,
            "peso_kg": self.peso_kg,
            "altura_cm": self.altura_cm,
            "tipo_sanguineo": self.tipo_sanguineo,
            "tabagismo": self.tabagismo,
            "consumo_alcool": self.consumo_alcool,
            "atividade_fisica": self.atividade_fisica,
            "qualidade_sono": self.qualidade_sono,
            "alimentacao_habitual": self.alimentacao_habitual,
            "alergias": [a.descricao for a in self.alergias],
            "historico_doencas": [{"doenca": h.doenca, "tipo": h.tipo} for h in self.historico_doencas],
        }


class Alergia(db.Model):
    __tablename__ = "alergias"

    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=False)
    tipo = db.Column(db.String(30))          
    descricao = db.Column(db.String(120), nullable=False)


class HistoricoDoenca(db.Model):
    __tablename__ = "historico_doencas"

    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=False)
    doenca = db.Column(db.String(120), nullable=False)
    tipo = db.Column(db.String(30))          
    observacoes = db.Column(db.Text)


class Sintoma(db.Model):
    __tablename__ = "sintomas"

    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=False)
    descricao = db.Column(db.String(200), nullable=False)
    intensidade = db.Column(db.Integer, default=5)     
    observacoes = db.Column(db.Text)
    data_inicio = db.Column(db.DateTime)                
    status = db.Column(db.String(20), default="em_analise")   
    data_registro = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "descricao": self.descricao,
            "intensidade": self.intensidade,
            "observacoes": self.observacoes,
            "data_inicio": self.data_inicio.strftime("%d/%m/%Y %H:%M") if self.data_inicio else None,
            "status": self.status,
            "data_registro": self.data_registro.strftime("%d/%m/%Y %H:%M"),
        }


class DiarioRegistro(db.Model):
    __tablename__ = "diario_registros"

    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=False)
    data = db.Column(db.Date, default=date.today)
    refeicao = db.Column(db.String(200))
    agua_copos = db.Column(db.Float, default=0)
    horas_sono = db.Column(db.Float, default=0)
    como_se_sentiu = db.Column(db.String(200))
    alimentacao = db.Column(db.Text)

    def to_dict(self):
        return {
            "id": self.id,
            "data": self.data.strftime("%d/%m/%Y"),
            "refeicao": self.refeicao,
            "agua_copos": self.agua_copos,
            "horas_sono": self.horas_sono,
            "como_se_sentiu": self.como_se_sentiu,
            "alimentacao": self.alimentacao,
        }


class Hospital(db.Model):
    __tablename__ = "hospitais"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    endereco = db.Column(db.String(200))

    profissionais = db.relationship("Profissional", backref="hospital")
    consultas = db.relationship("Consulta", backref="hospital")


class Profissional(db.Model):
    __tablename__ = "profissionais"

    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey("hospitais.id"), nullable=False)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    papel = db.Column(db.String(20), nullable=False)    
    registro_profissional = db.Column(db.String(40))    

    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def checar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)

    @property
    def papel_label(self):
        return {
            "admin": "Administrador",
            "medico": "Médico",
            "enfermeiro": "Enfermeiro",
            "analista": "Analista",
        }.get(self.papel, self.papel)


class RecomendacaoReceita(db.Model):
    
    __tablename__ = "recomendacoes"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, default=gerar_codigo_receita)
    profissional_id = db.Column(db.Integer, db.ForeignKey("profissionais.id"), nullable=False)
    paciente_alvo_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"))  

    titulo = db.Column(db.String(120), nullable=False)
    tipo = db.Column(db.String(30))          
    descricao = db.Column(db.Text, nullable=False)
    posologia = db.Column(db.String(200))    

    
    idade_min = db.Column(db.Integer)
    idade_max = db.Column(db.Integer)
    peso_min_kg = db.Column(db.Float)
    contraindicacoes_alergia = db.Column(db.String(300))  

    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    profissional = db.relationship("Profissional")
    paciente_alvo = db.relationship("Paciente", foreign_keys=[paciente_alvo_id])

    def to_dict(self):
        return {
            "id": self.id,
            "codigo": self.codigo,
            "titulo": self.titulo,
            "tipo": self.tipo,
            "descricao": self.descricao,
            "posologia": self.posologia,
            "idade_min": self.idade_min,
            "idade_max": self.idade_max,
            "peso_min_kg": self.peso_min_kg,
            "contraindicacoes_alergia": self.contraindicacoes_alergia,
            "profissional": self.profissional.nome if self.profissional else None,
        }


class ReceitaPaciente(db.Model):
    
    __tablename__ = "receitas_pacientes"

    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=False)
    recomendacao_id = db.Column(db.Integer, db.ForeignKey("recomendacoes.id"), nullable=False)

    status = db.Column(db.String(20))       
    motivo = db.Column(db.Text)
    iniciada = db.Column(db.Boolean, default=False)   
    vinculado_em = db.Column(db.DateTime, default=datetime.utcnow)

    recomendacao = db.relationship("RecomendacaoReceita")
    lembretes = db.relationship("Lembrete", backref="receita", cascade="all, delete-orphan")
    pedidos_farmacia = db.relationship("PedidoFarmacia", backref="receita_paciente",
                                        cascade="all, delete-orphan",
                                        order_by="PedidoFarmacia.criado_em.desc()")

    def to_dict(self):
        return {
            "id": self.id,
            "status": self.status,
            "motivo": self.motivo,
            "iniciada": self.iniciada,
            "vinculado_em": self.vinculado_em.strftime("%d/%m/%Y %H:%M"),
            "recomendacao": self.recomendacao.to_dict() if self.recomendacao else None,
            "pedidos_farmacia": [pf.to_dict() for pf in self.pedidos_farmacia],
        }


def gerar_link_online():
    return "https://cuidemais.app/consulta-online/" + "".join(random.choices(string.ascii_lowercase + string.digits, k=10))


class Consulta(db.Model):
    
    __tablename__ = "consultas"

    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=False)
    hospital_id = db.Column(db.Integer, db.ForeignKey("hospitais.id"), nullable=False)
    motivo = db.Column(db.String(200))
    data_hora = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default="agendada")   
    tipo = db.Column(db.String(20), default="presencial")   
    link_online = db.Column(db.String(200))                  

    def to_dict(self):
        return {
            "id": self.id,
            "hospital": self.hospital.nome if self.hospital else None,
            "motivo": self.motivo,
            "data_hora": self.data_hora.strftime("%d/%m/%Y %H:%M"),
            "status": self.status,
            "tipo": self.tipo,
            "link_online": self.link_online,
        }


class Notificacao(db.Model):
    
    __tablename__ = "notificacoes"

    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey("hospitais.id"), nullable=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=True)
    tipo = db.Column(db.String(30), nullable=False)   
    titulo = db.Column(db.String(150), nullable=False)
    mensagem = db.Column(db.String(300))
    lida = db.Column(db.Boolean, default=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    paciente = db.relationship("Paciente")

    ICONES = {
        "novo_paciente": "bi-person-plus",
        "atualizacao_paciente": "bi-pencil-square",
        "nova_consulta": "bi-calendar2-check",
    }

    @property
    def icone(self):
        return self.ICONES.get(self.tipo, "bi-bell")

    def to_dict(self):
        return {
            "id": self.id,
            "tipo": self.tipo,
            "titulo": self.titulo,
            "mensagem": self.mensagem,
            "lida": self.lida,
            "criado_em": self.criado_em.strftime("%d/%m/%Y %H:%M"),
        }


class Farmacia(db.Model):
    __tablename__ = "farmacias"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    endereco = db.Column(db.String(200))

    farmaceuticos = db.relationship("Farmaceutico", backref="farmacia", cascade="all, delete-orphan")
    pedidos = db.relationship("PedidoFarmacia", backref="farmacia")


class Farmaceutico(db.Model):
    __tablename__ = "farmaceuticos"

    id = db.Column(db.Integer, primary_key=True)
    farmacia_id = db.Column(db.Integer, db.ForeignKey("farmacias.id"), nullable=False)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)

    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def checar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)


class PedidoFarmacia(db.Model):

    __tablename__ = "pedidos_farmacia"

    id = db.Column(db.Integer, primary_key=True)
    receita_paciente_id = db.Column(db.Integer, db.ForeignKey("receitas_pacientes.id"), nullable=False)
    farmacia_id = db.Column(db.Integer, db.ForeignKey("farmacias.id"), nullable=False)
    farmaceutico_id = db.Column(db.Integer, db.ForeignKey("farmaceuticos.id"), nullable=True)

    status = db.Column(db.String(20), default="pendente")   # pendente / disponivel / indisponivel
    preco = db.Column(db.Float)
    observacao = db.Column(db.String(300))

    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    respondido_em = db.Column(db.DateTime)

    farmaceutico = db.relationship("Farmaceutico")

    def to_dict(self):
        receita = self.receita_paciente
        return {
            "id": self.id,
            "status": self.status,
            "preco": self.preco,
            "observacao": self.observacao,
            "farmacia": self.farmacia.nome if self.farmacia else None,
            "farmaceutico": self.farmaceutico.nome if self.farmaceutico else None,
            "criado_em": self.criado_em.strftime("%d/%m/%Y %H:%M"),
            "respondido_em": self.respondido_em.strftime("%d/%m/%Y %H:%M") if self.respondido_em else None,
            "medicacao": receita.recomendacao.titulo if receita and receita.recomendacao else None,
            "posologia": receita.recomendacao.posologia if receita and receita.recomendacao else None,
            "paciente": receita.paciente.nome if receita and receita.paciente else None,
            "paciente_referencia": receita.paciente.referencia if receita and receita.paciente else None,
        }


class Lembrete(db.Model):
    
    __tablename__ = "lembretes"

    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=False)
    receita_id = db.Column(db.Integer, db.ForeignKey("receitas_pacientes.id"))
    titulo = db.Column(db.String(120), nullable=False)
    hora = db.Column(db.String(5))          # "HH:MM"
    ativo = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "titulo": self.titulo,
            "hora": self.hora,
            "ativo": self.ativo,
        }

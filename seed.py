
from datetime import date

from app import create_app
from extensions import db
from models import Hospital, Profissional, Paciente, Alergia, RecomendacaoReceita, Farmacia, Farmaceutico

app = create_app()

with app.app_context():
    db.drop_all()
    db.create_all()

    hospital = Hospital(nome="Hospital São Lucas", endereco="Av. Principal, 100")
    db.session.add(hospital)
    db.session.flush()

    admin = Profissional(hospital_id=hospital.id, nome="Ana Costa", email="admin@hospital.com", papel="admin")
    admin.set_senha("admin123")

    medico = Profissional(hospital_id=hospital.id, nome="Dr. Marco Beltrão", email="medico@hospital.com",
                           papel="medico", registro_profissional="CRM-1234")
    medico.set_senha("medico123")

    enfermeiro = Profissional(hospital_id=hospital.id, nome="Dra. Helena Prado", email="enfermeiro@hospital.com",
                               papel="enfermeiro", registro_profissional="COREN-5678")
    enfermeiro.set_senha("enfermeiro123")

    analista = Profissional(hospital_id=hospital.id, nome="Carla Santos", email="analista@hospital.com", papel="analista")
    analista.set_senha("analista123")

    db.session.add_all([admin, medico, enfermeiro, analista])
    db.session.flush()

    paciente = Paciente(
        nome="Maria Silva", email="paciente@teste.com", telefone="+244 923 000 000",
        data_nascimento=date(1994, 5, 12), sexo="feminino", peso_kg=62, altura_cm=165,
        tipo_sanguineo="O+", tabagismo="nunca", consumo_alcool="social",
        atividade_fisica="moderado", qualidade_sono="regular",
        alimentacao_habitual="Frutas no café, almoço com salada.",
    )
    paciente.set_senha("paciente123")
    db.session.add(paciente)
    db.session.flush()

    db.session.add_all([
        Alergia(paciente_id=paciente.id, tipo="medicamento", descricao="dipirona"),
        Alergia(paciente_id=paciente.id, tipo="alimento", descricao="amendoim"),
    ])

    rec_compativel = RecomendacaoReceita(
        profissional_id=medico.id,
        titulo="Paracetamol 500mg (venda livre)",
        tipo="farmaco_venda_livre",
        descricao="Para febre acima de 37.8°C ou dor leve a moderada.",
        posologia="1 comprimido 500mg a cada 6h · máx. 4 doses/24h",
        idade_min=12, peso_min_kg=40,
        contraindicacoes_alergia="",
    )
    rec_incompativel = RecomendacaoReceita(
        profissional_id=enfermeiro.id,
        titulo="Dipirona 500mg (venda livre)",
        tipo="farmaco_venda_livre",
        descricao="Para febre alta ou dor moderada a forte.",
        posologia="1 comprimido a cada 8h · máx. 3 doses/24h",
        idade_min=18,
        contraindicacoes_alergia="dipirona",
    )
    db.session.add_all([rec_compativel, rec_incompativel])
    db.session.flush()

    farmacia = Farmacia(nome="Farmácia Central", endereco="Rua das Flores, 45")
    db.session.add(farmacia)
    db.session.flush()

    farmaceutico = Farmaceutico(farmacia_id=farmacia.id, nome="João Neto", email="farmaceutico@farmacia.com")
    farmaceutico.set_senha("farmacia123")
    db.session.add(farmaceutico)
    db.session.commit()

    print("Base de dados populada com sucesso!\n")
    print("== App do paciente (http://127.0.0.1:5000/login) ==")
    print(f"  email: paciente@teste.com  senha: paciente123")
    print(f"  referência para o hospital: {paciente.referencia}\n")
    print("== Dashboard do hospital (http://127.0.0.1:5000/dashboard/login) ==")
    print("  admin:      admin@hospital.com      / admin123")
    print("  médico:     medico@hospital.com     / medico123")
    print("  enfermeiro: enfermeiro@hospital.com / enfermeiro123")
    print("  analista:   analista@hospital.com   / analista123\n")
    print("Códigos de receita para testar 'Vincular receita' no app do paciente:")
    print(f"  {rec_compativel.codigo} -> Paracetamol (paciente é alérgico a Dipirona -> COMPATÍVEL)")
    print(f"  {rec_incompativel.codigo} -> Dipirona (paciente é alérgico a Dipirona -> INCOMPATÍVEL)")
    print("\n== Portal da farmácia (http://127.0.0.1:5000/farmacia/login) ==")
    print(f"  farmacêutico: farmaceutico@farmacia.com / farmacia123")

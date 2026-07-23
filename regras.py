


def verificar_compatibilidade(paciente, recomendacao):

    problemas = []

    idade = paciente.idade
    if idade is not None:
        if recomendacao.idade_min and idade < recomendacao.idade_min:
            problemas.append(
                f"Idade do paciente ({idade} anos) é menor que o mínimo exigido "
                f"({recomendacao.idade_min} anos)."
            )
        if recomendacao.idade_max and idade > recomendacao.idade_max:
            problemas.append(
                f"Idade do paciente ({idade} anos) é maior que o máximo permitido "
                f"({recomendacao.idade_max} anos)."
            )

    if recomendacao.peso_min_kg and paciente.peso_kg:
        if paciente.peso_kg < recomendacao.peso_min_kg:
            problemas.append(
                f"Peso do paciente ({paciente.peso_kg}kg) é menor que o mínimo "
                f"exigido ({recomendacao.peso_min_kg}kg)."
            )

    if recomendacao.contraindicacoes_alergia:
        contraindicados = [
            c.strip().lower()
            for c in recomendacao.contraindicacoes_alergia.split(",")
            if c.strip()
        ]
        alergias_paciente = [a.descricao.strip().lower() for a in paciente.alergias]

        conflitos = [
            c for c in contraindicados
            if any(c in a or a in c for a in alergias_paciente)
        ]
        if conflitos:
            problemas.append(
                "Paciente possui alergia registrada que contraindica esta "
                f"recomendação: {', '.join(conflitos)}."
            )

    if problemas:
        return "incompativel", " ".join(problemas)

    return "compativel", "Nenhuma restrição encontrada com base no histórico registrado do paciente."

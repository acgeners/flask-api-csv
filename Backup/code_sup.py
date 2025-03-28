VALID_DDD = {
    "11", "12", "13", "14", "15", "16", "17", "18", "19",  # SP
    "21", "22", "24",  # RJ
    "27", "28",  # ES
    "31", "32", "33", "34", "35", "37", "38",  # MG
    "41", "42", "43", "44", "45", "46",  # PR
    "47", "48", "49",  # SC
    "51", "53", "54", "55",  # RS
    "61",  # DF
    "62", "64",  # GO
    "63",  # TO
    "65", "66",  # MT
    "67",  # MS
    "68", "69",  # AC, RO
    "71", "73", "74", "75", "77",  # BA
    "79",  # SE
    "81", "87",  # PE
    "82",  # AL
    "83",  # PB
    "84",  # RN
    "85", "88",  # CE
    "86", "89",  # PI
    "91", "93", "94",  # PA
    "92", "97",  # AM
    "95",  # RR
    "96",  # AP
    "98", "99"  # MA
}


meses = [
    # Português
    "janeiro", "jan",
    "fevereiro", "fev",
    "março", "mar",
    "abril", "abr",
    "maio", "mai",
    "junho", "jun",
    "julho", "jul",
    "agosto", "ago",
    "setembro", "set",
    "outubro", "out",
    "novembro", "nov",
    "dezembro", "dez",
    # Inglês
    "January", "Jan",
    "February", "Feb",
    "March", "Mar",
    "April", "Apr",
    "May", "May",
    "June", "Jun",
    "July", "Jul",
    "August", "Aug",
    "September", "Sep",
    "October", "Oct",
    "November", "Nov",
    "December", "Dec"
]

# Criar a expressão regular com base na lista de meses
months = r"\b(" + "|".join(meses) + r")\b"

meses_pt = meses[:24]  # Pegando apenas os meses em português
meses_en = meses[24:]  # Pegando apenas os meses em inglês
month_translation = {pt: en for pt, en in zip(meses_pt, meses_en)}

ref_columns_list = ["Categoria de Stakeholder", "Nível de Relacionamento", "Canal Preferido",
                          "Função de Compra", "Função de Impacto", "Gênero", "Função de Formalização", "Função de Faturamento"]

ref_file = ["ref", "modelo", "referencia", "padrao", "arquivo_modelo"]
new_file = ["despadronizado", "new", "novo"]
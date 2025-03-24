from pathlib import Path

# Define a pasta onde estão os arquivos
pasta = Path("/Users/geners/Documents/02_Projeto_Scala")

# Obtém a lista de nomes dos arquivos na pasta e ordena alfabeticamente
arquivos = sorted([f.name for f in pasta.iterdir() if f.is_file()])

# Define o caminho do arquivo de saída
arquivo_saida = "lista_arquivos.txt"

# Escreve os nomes dos arquivos no .txt
with open(arquivo_saida, "w", encoding="utf-8") as f:
    for arquivo in arquivos:
        f.write(arquivo + "\n")  # Escreve cada nome de arquivo em uma linha
        print(arquivo)

print(f"Lista de arquivos salva em '{arquivo_saida}'")

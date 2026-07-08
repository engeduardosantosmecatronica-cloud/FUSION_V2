import os

# Liste aqui o que você quer que apareça (Pastas do Sistema a IGNORAR)
IGNORAR_PASTAS = {'__pycache__', '.git', '.vscode', '.idea','archive', 'venv', '.venv', 'venv_omnis'}
IGNORAR_ARQUIVOS = {'.DS_Store', 'desktop.ini''.csv'}

def gerar_arvore(caminho, prefixo=""):
    conteudo = sorted(os.listdir(caminho))
    # Filtra os itens ignorados
    itens = [item for item in conteudo if item not in IGNORAR_PASTAS and item not in IGNORAR_ARQUIVOS]
    
    linhas = []
    for i, item in enumerate(itens):
        caminho_completo = os.path.join(caminho, item)
        is_last = (i == len(itens) - 1)
        conector = "└── " if is_last else "├── "
        
        linhas.append(f"{prefixo}{conector}{item}")
        
        if os.path.isdir(caminho_completo):
            novo_prefixo = prefixo + ("    " if is_last else "│   ")
            linhas.extend(gerar_arvore(caminho_completo, novo_prefixo))
            
    return linhas

# Configurações
pasta_projeto = "." # Nome da sua pasta principal
arquivo_saida = "estrutura_limpa.txt"

print(f"Gerando estrutura para: {pasta_projeto}...")
arvore_final = [pasta_projeto + "/"] + gerar_arvore(pasta_projeto)

with open(arquivo_saida, "w", encoding="utf-8") as f:
    f.write("\n".join(arvore_final))

print(f"✅ Pronto! A estrutura limpa foi salva em: {arquivo_saida}")
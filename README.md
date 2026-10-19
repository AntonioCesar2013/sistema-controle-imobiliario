# ImobGestão — Controle Imobiliário

Esqueleto funcional de um sistema desktop local para proprietários, imóveis,
inquilinos, contratos de locação e mensalidades. A interface segue o padrão do
projeto **Controle Financeiro Clínica**, usando HTML/CSS/JavaScript dentro do
Microsoft Edge WebView2 e banco SQLite.

## Executar

No Windows, execute `iniciar.cmd`. Se necessário, instale antes:

```powershell
python -m pip install -r requirements.txt
python main.py
```

O banco é criado automaticamente em `dados/imobiliaria.db`.

## Popular o banco para demonstração

Com o sistema fechado, execute `popular_banco.cmd`. O processo inclui dados
totalmente fictícios e pode ser repetido sem duplicá-los. São criados:

- 3 proprietários, 4 inquilinos e 7 imóveis;
- 4 locações ativas e uma locação encerrada;
- contratos residenciais e comerciais, antecipados e postecipados;
- locações com e sem depósito caução;
- mensalidades pagas, abertas, futuras e atrasadas;
- um inquilino com mais de um contrato no histórico.

O populador não apaga nem altera cadastros reais. Os registros de demonstração
usam códigos iniciados por `DEMO-` e documentos reservados para teste.

## Regras já implementadas

- um proprietário pode possuir vários imóveis;
- cada imóvel possui exatamente um proprietário principal;
- um inquilino pode manter várias locações;
- um imóvel não pode ter duas locações ativas;
- locações residenciais e comerciais;
- aluguel antecipado ou postecipado;
- caução opcional e índice de reajuste;
- geração automática das mensalidades durante a vigência;
- identificação automática de parcelas atrasadas;
- baixa de recebimentos e painel de valores;
- visualização e impressão do contrato de locação.

O texto contratual fornecido é um modelo operacional inicial e deve ser revisado
por profissional jurídico antes de uso definitivo.

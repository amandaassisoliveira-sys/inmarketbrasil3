# Deploy no Railway — com banco de dados (novidade desta versão)

Esta versão adiciona login e simulações salvas, que precisam de um banco de dados
de verdade. São 2 passos novos além do processo de sempre.

## 1. Subir o código (igual sempre)
Suba a pasta `app/`, `requirements.txt` e `Procfile` para o GitHub, e conecte o
repositório ao Railway como já fizemos antes.

## 2. NOVO — Adicionar um banco Postgres
No painel do Railway, dentro do mesmo projeto:
1. Clique em "New" → "Database" → "Add PostgreSQL"
2. O Railway cria o banco sozinho e já disponibiliza a variável `DATABASE_URL`
   automaticamente para o seu serviço (não precisa copiar/colar nada)

## 3. NOVO — Variáveis de ambiente adicionais
Em "Variables" do seu serviço (não do banco), adicione:
- `JWT_SECRET` — qualquer string longa e aleatória (ex: gere uma em
  https://generate-secret.vercel.app/32)
- `SITE_URL` — a URL pública do seu backend no Railway (ex:
  `https://inmarketbrazil-production.up.railway.app`)
- `RESEND_API_KEY` — (opcional por enquanto) deixe em branco para testar; o link
  de acesso aparece direto na resposta da API em vez de ser enviado por email

## 4. Testar sem configurar email ainda
Com `RESEND_API_KEY` vazio, o endpoint `/auth/request-link` devolve um campo
`dev_verify_url` — abra esse link no navegador pra "logar" sem precisar receber
email de verdade. Isso é só para teste; configure o Resend antes de vender o
acesso de verdade.

## 5. Configurar o Resend (quando for usar de verdade)
1. Crie conta grátis em resend.com (3.000 emails/mês grátis)
2. Pegue a API Key em resend.com/api-keys
3. Cole em `RESEND_API_KEY` no Railway
4. O campo `from` (RESEND_FROM_EMAIL) só funciona com o domínio de teste deles
   (`onboarding@resend.dev`) até você verificar um domínio próprio — para
   começar a vender o curso, vale a pena verificar seu domínio no Resend

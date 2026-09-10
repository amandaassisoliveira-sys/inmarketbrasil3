import httpx
from .config import settings


async def enviar_link_magico(email: str, token: str) -> bool:
    """
    Envia o email com o link de acesso via Resend. Se RESEND_API_KEY não estiver
    configurada (modo de desenvolvimento), apenas imprime o link no log do servidor
    em vez de falhar — assim dá para testar o fluxo de login sem ter configurado
    o serviço de email ainda.
    """
    link = f"{settings.SITE_URL}/?login_token={token}"

    if not settings.RESEND_API_KEY:
        print(f"[EMAIL-DEV] RESEND_API_KEY não configurada. Link de acesso para {email}: {link}")
        return True

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": settings.RESEND_FROM_EMAIL,
                    "to": [email],
                    "subject": "Seu link de acesso — Simulador de Importação",
                    "html": (
                        "<p>Clique no link abaixo para entrar no Simulador de Importação:</p>"
                        f'<p><a href="{link}">{link}</a></p>'
                        "<p>Esse link expira em 15 minutos. Se você não pediu esse acesso, "
                        "pode ignorar este email.</p>"
                    ),
                },
            )
            return resp.status_code < 300
    except Exception as e:
        print(f"[EMAIL-ERRO] Falha ao enviar email para {email}: {e}")
        return False

"""F-310 Phase C — transactional email templates.

Two templates at Phase C MVP:
  - Email verification (post-registration + resend)
  - Password reset

Returns (subject, html, text) tuples for app.services.email.send_email().
HTML is intentionally minimal — Resend renders fine, and overflow into
real templates (Jinja files or MJML) is a Phase 2 polish task.

Bilingual (FR + EN) per the existing app pattern; lang param drives
which strings render. Defaults to "en" if missing/unknown.
"""
from __future__ import annotations

from app.config import settings


def _safe_lang(lang: str | None) -> str:
    return lang if lang in ("en", "fr") else "en"


def build_verification_email(
    *,
    to_email: str,
    raw_token: str,
    lang: str | None = "en",
) -> tuple[str, str, str]:
    """Return (subject, html, text) for the verification email."""
    lang = _safe_lang(lang)
    url = f"{settings.FRONTEND_PUBLIC_URL}/auth/verify-email?token={raw_token}"

    if lang == "fr":
        subject = "Le Méthodic — Vérifie ton adresse email"
        intro = "Bienvenue sur Le Méthodic."
        cta = "Vérifier mon email"
        body_pre = (
            "Pour activer ton compte, clique sur le bouton ci-dessous "
            "ou colle le lien dans ton navigateur."
        )
        body_post = "Le lien expire dans 24 heures."
        plain_intro = "Bienvenue. Vérifie ton email :"
        plain_expiry = "Le lien expire dans 24 heures."
    else:
        subject = "Le Méthodic — Verify your email"
        intro = "Welcome to Le Méthodic."
        cta = "Verify my email"
        body_pre = (
            "To activate your account, click the button below or paste "
            "the link into your browser."
        )
        body_post = "The link expires in 24 hours."
        plain_intro = "Welcome. Please verify your email:"
        plain_expiry = "The link expires in 24 hours."

    html = f"""<!doctype html>
<html><body style="font-family:-apple-system,Segoe UI,sans-serif;color:#1a1a1a;line-height:1.5;max-width:560px;margin:0 auto;padding:32px 24px;">
  <h1 style="font-size:22px;margin-bottom:16px;">{intro}</h1>
  <p style="margin:0 0 24px;">{body_pre}</p>
  <p style="margin:24px 0;">
    <a href="{url}" style="display:inline-block;background:#1a1a1a;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:500;">{cta}</a>
  </p>
  <p style="font-size:13px;color:#666;margin:24px 0 0;"><a href="{url}" style="color:#666;word-break:break-all;">{url}</a></p>
  <p style="font-size:13px;color:#666;margin:16px 0 0;">{body_post}</p>
</body></html>"""

    text = f"{plain_intro}\n\n{url}\n\n{plain_expiry}\n"
    return subject, html, text


def build_password_reset_email(
    *,
    to_email: str,
    raw_token: str,
    lang: str | None = "en",
) -> tuple[str, str, str]:
    """Return (subject, html, text) for the password-reset email."""
    lang = _safe_lang(lang)
    url = f"{settings.FRONTEND_PUBLIC_URL}/auth/reset-password?token={raw_token}"

    if lang == "fr":
        subject = "Le Méthodic — Réinitialisation du mot de passe"
        intro = "Demande de réinitialisation reçue."
        cta = "Choisir un nouveau mot de passe"
        body_pre = (
            "Si tu n'es pas à l'origine de cette demande, ignore cet "
            "email. Aucun changement ne sera fait."
        )
        body_post = "Le lien expire dans 1 heure."
        plain_intro = "Demande de réinitialisation. Lien :"
        plain_expiry = "Le lien expire dans 1 heure."
    else:
        subject = "Le Méthodic — Reset your password"
        intro = "Password reset request received."
        cta = "Choose a new password"
        body_pre = (
            "If you didn't request this, ignore this email. No changes "
            "will be made."
        )
        body_post = "The link expires in 1 hour."
        plain_intro = "Password reset link:"
        plain_expiry = "The link expires in 1 hour."

    html = f"""<!doctype html>
<html><body style="font-family:-apple-system,Segoe UI,sans-serif;color:#1a1a1a;line-height:1.5;max-width:560px;margin:0 auto;padding:32px 24px;">
  <h1 style="font-size:22px;margin-bottom:16px;">{intro}</h1>
  <p style="margin:24px 0;">
    <a href="{url}" style="display:inline-block;background:#1a1a1a;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:500;">{cta}</a>
  </p>
  <p style="font-size:13px;color:#666;margin:24px 0 0;"><a href="{url}" style="color:#666;word-break:break-all;">{url}</a></p>
  <p style="font-size:14px;color:#1a1a1a;margin:24px 0 0;">{body_pre}</p>
  <p style="font-size:13px;color:#666;margin:8px 0 0;">{body_post}</p>
</body></html>"""

    text = f"{plain_intro}\n\n{url}\n\n{body_pre}\n\n{plain_expiry}\n"
    return subject, html, text

import smtplib
from email.message import EmailMessage

from flask import current_app


class EmailError(Exception):
    """Erreur de base pour les échecs d'envoi email."""


class EmailConfigurationError(EmailError):
    """Levée lorsque la configuration SMTP est absente ou incomplète."""


class EmailDeliveryError(EmailError):
    """Levée lorsque le serveur SMTP refuse ou échoue pendant l'envoi."""


def _required_mail_config():
    server = current_app.config.get('MAIL_SERVER', '')
    sender = current_app.config.get('MAIL_DEFAULT_SENDER', '')
    if not server or not sender:
        raise EmailConfigurationError(
            'Email service is not configured. Set MAIL_SERVER and MAIL_DEFAULT_SENDER.'
        )
    return server, sender


def send_email(recipients, subject, body):
    """Envoie un email texte via SMTP et lève une exception explicite en cas d'échec."""
    if isinstance(recipients, str):
        recipients = [recipients]
    recipients = [r for r in (recipients or []) if r]
    if not recipients:
        raise EmailConfigurationError('At least one email recipient is required.')

    server, sender = _required_mail_config()
    msg = EmailMessage()
    msg['From'] = sender
    msg['To'] = ', '.join(recipients)
    msg['Subject'] = subject
    msg.set_content(body)

    port = current_app.config.get('MAIL_PORT', 587)
    timeout = current_app.config.get('MAIL_TIMEOUT', 10)
    username = current_app.config.get('MAIL_USERNAME', '')
    password = current_app.config.get('MAIL_PASSWORD', '')
    use_tls = current_app.config.get('MAIL_USE_TLS', True)
    use_ssl = current_app.config.get('MAIL_USE_SSL', False)

    smtp_cls = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
    try:
        with smtp_cls(server, port, timeout=timeout) as smtp:
            if use_tls and not use_ssl:
                smtp.starttls()
            if username:
                smtp.login(username, password)
            smtp.send_message(msg)
    except (OSError, smtplib.SMTPException) as exc:
        raise EmailDeliveryError(f'Email delivery failed: {exc}') from exc

    return {'recipients': recipients, 'subject': subject}

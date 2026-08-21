import json
import logging
import re
import threading
import urllib.error
import urllib.request
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


class EmailService:
    """Service to send branded HTML emails for Stephotec Computer Technologies Ltd."""

    @staticmethod
    def _send_via_brevo(api_key, from_email, to_email, subject, html_content, text_content):
        url = "https://api.brevo.com/v3/smtp/email"
        sender_name = "Stephotec Support"
        sender_email = getattr(settings, "EMAIL_HOST_USER", "info@stephotec.com")
        if "<" in from_email and ">" in from_email:
            sender_name = from_email.split("<")[0].strip().strip('"')
            sender_email = from_email.split("<")[1].split(">")[0].strip()

        payload = {
            "sender": {"name": sender_name, "email": sender_email},
            "to": [{"email": to_email}],
            "subject": subject,
            "htmlContent": html_content,
            "textContent": text_content,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "api-key": api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status in [200, 201, 202]

    @staticmethod
    def _send_via_resend(api_key, from_email, to_email, subject, html_content, text_content):
        url = "https://api.resend.com/emails"
        payload = {
            "from": from_email,
            "to": [to_email],
            "subject": subject,
            "html": html_content,
            "text": text_content,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status in [200, 201, 202]

    @classmethod
    def _dispatch_send(cls, msg, subject, to_email, html_content, text_content, from_email):
        brevo_key = getattr(settings, "BREVO_API_KEY", "").strip()
        resend_key = getattr(settings, "RESEND_API_KEY", "").strip()

        try:
            if brevo_key:
                print(f"[EMAIL SENDING] Sending '{subject}' to {to_email} via Brevo HTTPS API (Port 443)...", flush=True)
                cls._send_via_brevo(brevo_key, from_email, to_email, subject, html_content, text_content)
                logger.info(f"Email '{subject}' successfully sent to {to_email} via Brevo API")
                print(f"[EMAIL SUCCESS] Email '{subject}' successfully delivered to {to_email} via Brevo!", flush=True)
                return

            if resend_key:
                print(f"[EMAIL SENDING] Sending '{subject}' to {to_email} via Resend HTTPS API (Port 443)...", flush=True)
                cls._send_via_resend(resend_key, from_email, to_email, subject, html_content, text_content)
                logger.info(f"Email '{subject}' successfully sent to {to_email} via Resend API")
                print(f"[EMAIL SUCCESS] Email '{subject}' successfully delivered to {to_email} via Resend!", flush=True)
                return

            # Default Standard SMTP
            print(f"[EMAIL SENDING] Attempting to send '{subject}' to {to_email} via host={getattr(settings, 'EMAIL_HOST', None)} port={getattr(settings, 'EMAIL_PORT', None)} TLS={getattr(settings, 'EMAIL_USE_TLS', None)} SSL={getattr(settings, 'EMAIL_USE_SSL', None)} user={getattr(settings, 'EMAIL_HOST_USER', None)}...", flush=True)
            msg.send(fail_silently=False)
            logger.info(f"Email '{subject}' successfully sent to {to_email}")
            print(f"[EMAIL SUCCESS] Email '{subject}' successfully sent to {to_email}!", flush=True)
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}", exc_info=True)
            print(f"[EMAIL FAILED] Failed to send email to {to_email}: {repr(e)}", flush=True)

    @classmethod
    def _clean_plain_text(cls, html_content):
        # Remove <style> and <script> contents entirely so CSS does not leak into plain text
        clean = re.sub(r'<(style|script)[^>]*>[\s\S]*?</\1>', '', html_content, flags=re.IGNORECASE)
        # Convert break and paragraph tags to newlines
        clean = re.sub(r'<br\s*/?>', '\n', clean, flags=re.IGNORECASE)
        clean = re.sub(r'</p>', '\n\n', clean, flags=re.IGNORECASE)
        clean = re.sub(r'</div>', '\n', clean, flags=re.IGNORECASE)
        # Strip remaining tags
        clean = strip_tags(clean)
        # Normalize whitespace and excessive blank lines
        clean = re.sub(r'[ \t]+', ' ', clean)
        clean = re.sub(r'\n\s*\n\s*\n+', '\n\n', clean)
        return clean.strip()

    @classmethod
    def _send_email(cls, to_email, subject, html_content, text_content=None, async_send=True):
        if not to_email:
            logger.warning("No recipient email provided for EmailService.")
            return False

        if not text_content:
            text_content = cls._clean_plain_text(html_content)

        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "Stephotec Computer Technologies Ltd <info@stephotec.com>")
        reply_to_email = getattr(settings, "EMAIL_HOST_USER", None) or "info@stephotec.com"

        try:
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=[to_email],
                reply_to=[reply_to_email],
                headers={
                    "Auto-Submitted": "auto-generated",
                    "X-Auto-Response-Suppress": "All",
                }
            )
            msg.attach_alternative(html_content, "text/html")

            if async_send:
                t = threading.Thread(
                    target=cls._dispatch_send,
                    args=(msg, subject, to_email, html_content, text_content, from_email),
                    daemon=True,
                )
                t.start()
            else:
                cls._dispatch_send(msg, subject, to_email, html_content, text_content, from_email)
            return True
        except Exception as e:
            logger.error(f"Failed to initialize email to {to_email}: {str(e)}")
            return False

    @classmethod
    def send_password_reset_email(cls, user, reset_url):
        subject = "Password Reset Request — Stephotec Computer Technologies Ltd"
        full_name = user.get_full_name() or user.username

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; color: #1e293b; }}
            .container {{ max-width: 580px; margin: 0 auto; background: #ffffff; border-radius: 12px; padding: 32px; border: 1px solid #e2e8f0; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
            .header {{ text-align: center; padding-bottom: 24px; border-bottom: 2px solid #7c3aed; }}
            .brand {{ font-size: 22px; font-weight: 800; color: #0f172a; letter-spacing: 0.5px; }}
            .subbrand {{ font-size: 11px; font-weight: 700; color: #7c3aed; letter-spacing: 1px; margin-top: 2px; }}
            .content {{ padding: 28px 0; font-size: 15px; line-height: 1.6; }}
            .btn {{ display: inline-block; background-color: #7c3aed; color: #ffffff !important; padding: 14px 32px; border-radius: 8px; font-weight: 700; text-decoration: none; margin: 20px 0; font-size: 15px; text-align: center; }}
            .btn:hover {{ background-color: #6d28d9; }}
            .footer {{ border-top: 1px solid #f1f5f9; padding-top: 20px; font-size: 12px; color: #64748b; text-align: center; line-height: 1.5; }}
            .warning {{ background-color: #fef2f2; border-left: 4px solid #ef4444; padding: 12px; border-radius: 4px; font-size: 13px; color: #991b1b; margin-top: 16px; }}
          </style>
        </head>
        <body>
          <div class="container">
            <div class="header">
              <div class="brand">STEPHOTEC</div>
              <div class="subbrand">COMPUTER TECHNOLOGIES LTD</div>
            </div>
            <div class="content">
              <p>Hello <strong>{full_name}</strong>,</p>
              <p>We received a request to reset your password for your Stephotec Student Account (<strong>{user.username}</strong>).</p>
              <p>Click the button below to reset your password. This link will expire in 24 hours:</p>
              <div style="text-align: center;">
                <a href="{reset_url}" class="btn" target="_blank">Reset Password Now</a>
              </div>
              <p>If the button above does not work, copy and paste the following link into your browser:</p>
              <p style="word-break: break-all; font-size: 13px; color: #2563eb;"><a href="{reset_url}">{reset_url}</a></p>
              <div class="warning">
                <strong>Security Alert:</strong> If you did not request a password reset, please ignore this email or contact support immediately. Your account remains secure.
              </div>
            </div>
            <div class="footer">
              <p><strong>Stephotec Computer Technologies Ltd</strong><br/>
              info@stephotec.com | +234 802 250 8370 | WhatsApp: +234 703 563 1513</p>
            </div>
          </div>
        </body>
        </html>
        """
        return cls._send_email(user.email, subject, html_content)

    @classmethod
    def send_welcome_account_email(cls, user, temp_password, activation_url):
        subject = "Welcome to Stephotec — Your Student Portal Account & Activation Link"
        full_name = user.get_full_name() or user.username
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
        login_url = f"{frontend_url}/login"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <style>
            body {{ font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif; background-color: #f1f5f9; margin: 0; padding: 24px 12px; color: #1e293b; }}
            .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 16px; padding: 36px 32px; border: 1px solid #e2e8f0; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.06); }}
            .header {{ text-align: center; padding-bottom: 24px; border-bottom: 2px solid #2563eb; }}
            .brand {{ font-size: 24px; font-weight: 900; color: #0f172a; letter-spacing: 0.5px; }}
            .subbrand {{ font-size: 11px; font-weight: 700; color: #2563eb; letter-spacing: 1.5px; text-transform: uppercase; margin-top: 3px; }}
            .content {{ padding: 28px 0 16px 0; font-size: 15px; line-height: 1.6; color: #334155; }}
            .cred-card {{ background: #f8fafc; border: 1.5px dashed #cbd5e1; border-radius: 12px; padding: 20px; margin: 24px 0; }}
            .cred-row {{ margin-bottom: 12px; }}
            .cred-row:last-child {{ margin-bottom: 0; }}
            .cred-label {{ font-size: 11px; font-weight: 800; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; display: block; margin-bottom: 4px; }}
            .cred-val {{ font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; font-size: 16px; font-weight: 700; color: #0f172a; background: #ffffff; padding: 6px 12px; border-radius: 6px; border: 1px solid #e2e8f0; display: inline-block; }}
            .btn-wrap {{ text-align: center; margin: 28px 0 20px 0; }}
            .btn {{ display: inline-block; background-color: #2563eb; color: #ffffff !important; padding: 15px 36px; border-radius: 10px; font-weight: 800; text-decoration: none; font-size: 15px; letter-spacing: 0.3px; box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3); }}
            .fallback-box {{ background-color: #f8fafc; border-radius: 8px; padding: 14px 18px; margin: 20px 0; font-size: 13px; color: #475569; border-left: 4px solid #3b82f6; }}
            .footer {{ border-top: 1px solid #f1f5f9; padding-top: 24px; margin-top: 24px; font-size: 12px; color: #94a3b8; text-align: center; line-height: 1.6; }}
          </style>
        </head>
        <body>
          <div class="container">
            <div class="header">
              <div class="brand">STEPHOTEC</div>
              <div class="subbrand">Computer Technologies Ltd · Student Portal</div>
            </div>
            <div class="content">
              <p style="font-size: 16px;">Hello <strong>{full_name}</strong>,</p>
              <p>Welcome to Stephotec! Your official student account has been successfully created on our student learning portal. Here are your access credentials:</p>
              
              <div class="cred-card">
                <div class="cred-row">
                  <span class="cred-label">Student ID / Username</span>
                  <span class="cred-val">{user.username}</span>
                </div>
                <div class="cred-row" style="margin-top: 14px;">
                  <span class="cred-label">Temporary Password</span>
                  <span class="cred-val" style="color: #d97706;">{temp_password}</span>
                </div>
              </div>

              <p>Please click the button below to activate your student profile and set your personal permanent password:</p>
              
              <div class="btn-wrap">
                <a href="{activation_url}" class="btn" target="_blank">Activate Your Profile Now</a>
              </div>

              <div class="fallback-box">
                <strong>Alternative Manual Login:</strong><br/>
                If you prefer or if the button doesn't open, visit our portal at <a href="{login_url}" style="color: #2563eb; font-weight: 700;">{login_url}</a>, log in using your <strong>Student ID</strong> and <strong>Temporary Password</strong>, and you will be guided to complete your profile activation.
              </div>

              <p style="font-size: 12px; color: #64748b; word-break: break-all; margin-top: 20px;">
                Direct activation link: <a href="{activation_url}" style="color: #2563eb;">{activation_url}</a>
              </p>
            </div>
            
            <div class="footer">
              <p><strong>Stephotec Computer Technologies Ltd</strong><br/>
              Empowering Tech Leaders · info@stephotec.com · +234 802 250 8370<br/>
              This is an automated notification. Please do not reply directly to this email.</p>
            </div>
          </div>
        </body>
        </html>
        """

        text_content = f"""Hello {full_name},

Welcome to Stephotec Computer Technologies Ltd! Your official student account has been created on the student portal.

YOUR ACCESS CREDENTIALS:
- Student ID / Username: {user.username}
- Temporary Password: {temp_password}

ACTIVATE YOUR PROFILE:
Please click the link below to activate your account and choose your permanent password:
{activation_url}

ALTERNATIVE MANUAL LOGIN:
You can also visit {login_url} and sign in using your Student ID ({user.username}) and Temporary Password.

Best regards,
Stephotec Computer Technologies Ltd
Empowering Tech Leaders
info@stephotec.com | +234 802 250 8370
"""
        return cls._send_email(user.email, subject, html_content, text_content=text_content)

    @classmethod
    def send_notification_email(cls, user, title, message):
        if not user.email:
            return False

        subject = f"{title} — Stephotec Portal Notification"
        full_name = user.get_full_name() or user.username

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; color: #1e293b; }}
            .container {{ max-width: 580px; margin: 0 auto; background: #ffffff; border-radius: 12px; padding: 32px; border: 1px solid #e2e8f0; }}
            .header {{ text-align: center; padding-bottom: 20px; border-bottom: 2px solid #7c3aed; }}
            .brand {{ font-size: 20px; font-weight: 800; color: #0f172a; }}
            .subbrand {{ font-size: 10px; font-weight: 700; color: #7c3aed; letter-spacing: 1px; }}
            .content {{ padding: 24px 0; font-size: 15px; line-height: 1.6; }}
            .footer {{ border-top: 1px solid #f1f5f9; padding-top: 16px; font-size: 12px; color: #64748b; text-align: center; }}
          </style>
        </head>
        <body>
          <div class="container">
            <div class="header">
              <div class="brand">STEPHOTEC</div>
              <div class="subbrand">COMPUTER TECHNOLOGIES LTD</div>
            </div>
            <div class="content">
              <p>Hello <strong>{full_name}</strong>,</p>
              <h3 style="color: #7c3aed; margin-top: 0;">{title}</h3>
              <p>{message}</p>
            </div>
            <div class="footer">
              <p>Stephotec Computer Technologies Ltd | info@stephotec.com</p>
            </div>
          </div>
        </body>
        </html>
        """
        return cls._send_email(user.email, subject, html_content)
